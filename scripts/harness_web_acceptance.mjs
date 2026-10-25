#!/usr/bin/env node
/** Real Chromium + published Web profile, with separately labelled fixture/live model lanes. */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { randomUUID, createHash } from 'node:crypto'
import { parseArgs } from 'node:util'

const { values } = parseArgs({ options: { deployment: { type: 'string' }, 'run-id': { type: 'string' },
  output: { type: 'string' }, mode: { type: 'string', default: 'fixture' },
  reuse: { type: 'string' },
  chromium: { type: 'string', default: '/usr/bin/chromium' } } })
if (!values.deployment || !values['run-id'] || !values.output) throw new Error('Provide --deployment, --run-id, and --output')
if (!['fixture', 'live'].includes(values.mode)) throw new Error('--mode must be fixture or live')
if (values.mode === 'live' && !values.reuse && !process.env.DEEPSEEK_API_KEY) throw new Error('The live lane requires DEEPSEEK_API_KEY in the environment')
const previous = values.reuse ? JSON.parse(await readFile(resolve(values.reuse), 'utf8')) : null
if (previous) {
  assert.equal(previous.mode, values.mode)
  assert.equal(previous.run_id, values['run-id'])
  assert.ok(previous.agent?.completed && previous.session_id, 'Replay requires a genuinely completed prior model turn')
  assert.notEqual(resolve(values.reuse), resolve(values.output), 'Replay must preserve the original receipt')
}
const deployment = JSON.parse(await readFile(resolve(values.deployment), 'utf8'))
assert.equal(deployment.harness_version, '0.2.1-rc.3')
const output = resolve(values.output)
await mkdir(dirname(output), { recursive: true })
const auditPath = output.replace(/\.json$/, '') + '.agent.json'
const overlay = output.replace(/\.json$/, '') + '.patch.yml'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.ACYCLE_PLAYWRIGHT_MODULE || 'playwright')
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
const run = JSON.parse(await readFile(join(deployment.workspace, '.acycle/runs', values['run-id'], 'result.json'), 'utf8'))
const pngs = Object.entries(run.artifacts).filter(([, path]) => path.endsWith('.png'))
assert.ok(pngs.length, 'The supplied completed run must have existing MATLAB PNGs')
const expected = await Promise.all(pngs.map(async ([key, path]) => ({ key, path, sha256: hash(await readFile(path)) })))
const patch = [{ id: 'session-title-llm', disabled: true }, { insert: [{
  id: 'acycle-web-acceptance-fixture', name: pathToFileURL(join(dirname(fileURLToPath(import.meta.url)), 'harness_web_fixture.mjs')).href,
  config: { runtime: deployment.runtime, mode: previous ? 'replay' : values.mode, runId: values['run-id'], audit: auditPath },
}] }]
if (values.mode === 'fixture') patch.push({ id: 'agent-default-model', config: { provider: 'acycle-ui-fixture', model: 'fixture-text' } })
await writeFile(overlay, JSON.stringify(patch, null, 2) + '\n')
const env = { ...process.env, ...deployment.environment }
if (values.mode === 'fixture' || previous) delete env.DEEPSEEK_API_KEY
const server = spawn(deployment.node, [deployment.cli, '--profile', deployment.profile, '--patch', overlay,
  '--host', '127.0.0.1', '--port', String(deployment.port), '--no-open'], {
  cwd: deployment.workspace, env, stdio: ['ignore', 'pipe', 'pipe'], detached: process.platform !== 'win32',
})
let logs = '', browser
server.stdout.on('data', chunk => { logs += chunk.toString() })
server.stderr.on('data', chunk => { logs += chunk.toString() })
const receipt = { schema_version: 1, status: 'running', mode: values.mode, fixture_adapter: values.mode === 'fixture',
  scope: 'Published official Web profile and actual Acycle preset in Chromium; existing MATLAB files only. Fixture mode is not a real-model autonomy or vision test.',
  runtime_version: deployment.harness_version, run_id: values['run-id'], expected_files: expected,
  main_chat_images: [], lightbox: false, refreshed: false, scientific_recalculation: false, screenshots: [] }
if (previous) receipt.reuse = { original_receipt: resolve(values.reuse), session_id: previous.session_id,
  new_user_prompt: false, new_model_requests_allowed: false, model_evidence_from_prior_completed_turn: true,
  prior_model_plugin_sha256: previous.plugin_sha256, prior_model_attachments_sha256: previous.attachments_sha256 }
receipt.plugin_sha256 = hash(await readFile(deployment.native_plugin))
receipt.attachments_sha256 = hash(await readFile(join(dirname(deployment.native_plugin), 'attachments.mjs')))
const waitFor = async (check, timeout = 120000) => {
  const start = Date.now()
  for (;;) {
    const result = await check()
    if (result) return result
    if (Date.now() - start > timeout) throw new Error('Timed out waiting for the Web acceptance condition')
    await new Promise(resolve => setTimeout(resolve, 200))
  }
}
try {
  const authenticatedUrl = await waitFor(() => {
    if (server.exitCode !== null) throw new Error('Web process exited before startup: ' + logs.replace(/https?:\/\/\S+/g, '[URL]'))
    return logs.match(/https?:\/\/127\.0\.0\.1:\d+\/[^\s\u001b]*token[^\s\u001b]*/)?.[0]
  })
  browser = await chromium.launch({ executablePath: values.chromium, headless: true, args: ['--no-sandbox'] })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, locale: 'en-US' })
  const page = await context.newPage()
  const media = new Map()
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname === '/api/file') media.set(url.searchParams.get('path'), response.status())
  })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(authenticatedUrl, { waitUntil: 'load' })
  const rpc = (method, request) => page.evaluate(async ({ method, request }) => {
    const response = await fetch('/api/' + method, { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ type: 'client-request', rpcId: crypto.randomUUID(), method, payload: { args: { request } } }) })
    const data = await response.json()
    if (!response.ok) throw new Error(JSON.stringify(data))
    return data
  }, { method, request })
  const unwrap = value => value.result?.value ?? value.result ?? value.payload?.value ?? value.payload ?? value
  let sessionId = previous?.session_id
  if (!previous) {
    const workspace = unwrap(await rpc('workspace/create', { path: deployment.workspace }))
    receipt.workspace_response = workspace
    const created = unwrap(await rpc('session/create', { workspaceId: workspace.workspaceId ?? workspace.id ?? workspace.workspace?.workspaceId ?? workspace.workspace?.id,
      agentPreset: deployment.preset }))
    receipt.session_response = created
    sessionId = created.sessionId ?? created.session?.id
  }
  assert.ok(sessionId, 'session/create must return a genuine Session ID')
  receipt.session_id = sessionId
  await page.evaluate(id => localStorage.setItem('dsh.sessions.current', JSON.stringify({ sessionId: id })), sessionId)
  await page.reload({ waitUntil: 'load' })
  if (!previous) await rpc('session/prompt', { requestId: randomUUID(), sessionId, mode: 'queue', clientTimeZone: 'UTC',
    content: [{ type: 'text', text: `请展示已完成运行 ${values['run-id']} 的频谱图与演化图，直接放在主聊天回复中，并附原始文件入口。请核查图件；不要启动任何新的科学计算。` }] })
  const audit = previous?.agent ?? await waitFor(async () => {
    try { const value = JSON.parse(await readFile(auditPath, 'utf8')); return value.completed ? value : null }
    catch { return null }
  }, values.mode === 'live' ? 300000 : 120000)
  receipt.agent = audit
  assert.equal(audit.preset, deployment.preset)
  assert.equal(audit.acycle_persona, true)
  assert.equal(audit.acycle_workflow_policy, true)
  assert.ok(audit.actual_agent_skills.includes('acycle-mini-robot'))
  assert.ok(audit.actual_agent_skills.includes('acycle-intake'))
  assert.ok(audit.model_visible_skill_catalog.includes('acycle-mini-robot'))
  assert.ok(audit.model_visible_skill_catalog.includes('acycle-intake'))
  assert.equal(audit.actual_agent_skills.filter(name => name.startsWith('acycle-')).length, 10)
  assert.equal(audit.model_visible_skill_catalog.filter(name => name.startsWith('acycle-')).length, 10)
  assert.equal(audit.headers[0].tool_names.filter(name => name.startsWith('acycle_')).length, 13)
  assert.ok(audit.deepseek_catalog?.inputModalities?.includes('image'), 'configured official model must declare image input')
  assert.equal(audit.scientific_calls.length, 0, 'UI acceptance must not request scientific recalculation')
  assert.ok(audit.tools.some(tool => tool.name === 'acycle_get_run'))
  if (values.mode === 'live') {
    assert.ok(audit.headers.some(header => header.config?.provider === 'deepseek-official' && header.config?.model === 'deepseek-flash'))
    const pixels = audit.image_results.filter(image => !image.offloaded)
    assert.ok(pixels.length > 0, 'The live visual-review lane must return actual read_image pixels')
    const index = JSON.parse(await readFile(join(deployment.dsh_home, 'llm-deepseek/files-v3.json'), 'utf8'))
    const uploads = index.records.filter(record => pixels.some(image => image.attachment.attachmentId === record.attachmentId))
    assert.ok(uploads.length > 0, 'A successful subsequent DeepSeek request must upload retained image bytes')
    receipt.model_visual_input = { provider: 'deepseek-official', model: 'deepseek-flash',
      retained_image_count: pixels.length, uploads: uploads.map(record => ({ attachment_id: record.attachmentId,
        bytes: record.bytes, remote_file_id_present: Boolean(record.fileId) })) }
  }
  const figures = expected.filter(item => /spectrum|evolution/.test(item.key))
  assert.ok(figures.length >= 2, 'This acceptance case expects spectrum and evolution PNGs')
  const loadMainChatFigure = async figure => {
    const image = page.locator('[data-chat-flow-kind="assistant-step"] img')
    return waitFor(async () => {
      await image.evaluateAll((nodes, target) => {
        const matching = nodes.find(node => node.alt.includes(target.key) ||
          decodeURIComponent(node.currentSrc || node.src).includes(target.path))
        matching?.scrollIntoView({ block: 'center', behavior: 'instant' })
      }, figure)
      const images = await image.evaluateAll(nodes => nodes.map(node => ({ alt: node.alt, src: node.currentSrc,
        width: node.naturalWidth, height: node.naturalHeight, sidebar: Boolean(node.closest('[data-rightbar-col]')) })))
      const found = images.find(item => !item.sidebar && (item.alt.includes(figure.key) || decodeURIComponent(item.src).includes(figure.path)) && item.width > 0)
      return found ?? null
    })
  }
  for (const figure of figures) {
    const found = await loadMainChatFigure(figure)
    receipt.main_chat_images.push({ ...found, original_path: figure.path })
    assert.equal(media.get(figure.path), 200)
  }
  const first = receipt.main_chat_images[0]
  await page.getByRole('button', { name: 'View full image: ' + first.alt, exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Image preview' })
  await dialog.waitFor({ state: 'visible' })
  await waitFor(() => dialog.getByRole('img').evaluateAll(images => images.some(image => image.naturalWidth > 0)))
  receipt.lightbox = true
  const lightboxShot = output.replace(/\.json$/, '') + '.lightbox.png'
  await page.screenshot({ path: lightboxShot })
  receipt.screenshots.push(lightboxShot)
  await page.getByRole('button', { name: 'Close image preview', exact: true }).click()
  await page.reload({ waitUntil: 'load' })
  for (const figure of figures) await loadMainChatFigure(figure)
  assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('dsh.sessions.current')).sessionId), sessionId)
  receipt.refreshed = true
  for (const figure of receipt.main_chat_images) {
    const image = page.locator('[data-chat-flow-kind="assistant-step"]').getByRole('img', { name: figure.alt, exact: true })
    await image.evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }))
    await page.waitForTimeout(350)
    assert.ok(await image.isVisible())
    const screenshot = output.replace(/\.json$/, '') + `.chat-${figure.original_path.endsWith('evolution.png') ? 'evolution' : 'spectrum'}.png`
    await page.screenshot({ path: screenshot })
    receipt.screenshots.push(screenshot)
  }
  receipt.downloads = []
  for (const extension of ['.png', '.csv', '.mat', '.fig']) {
    const path = Object.values(run.artifacts).find(path => path.endsWith(extension))
    assert.ok(path, 'The existing run must include ' + extension)
    const response = await page.request.get(new URL('/api/file?path=' + encodeURIComponent(path), page.url()).href)
    assert.equal(response.status(), 200)
    const bytes = await response.body()
    assert.equal(hash(bytes), hash(await readFile(path)), 'Original file download must preserve bytes')
    receipt.downloads.push({ extension, path, bytes: bytes.length, sha256: hash(bytes) })
  }
  const chatShot = output.replace(/\.json$/, '') + '.chat-refreshed.png'
  await page.screenshot({ path: chatShot })
  receipt.screenshots.push(chatShot)
  receipt.page_errors = errors
  assert.deepEqual(errors, [])
  if (previous) {
    const replay = JSON.parse(await readFile(auditPath, 'utf8'))
    assert.equal(replay.headers.length, 0, 'Browser replay must not make another model request')
    assert.equal(replay.tools.length, 0, 'Browser replay must not execute another tool')
    assert.equal(replay.blocked_model_requests, 0, 'Browser replay must not attempt another model request')
    assert.deepEqual(replay.blocked_tool_calls, [], 'Browser replay must not attempt another tool')
    receipt.reuse.observed_new_model_requests = replay.headers.length
    receipt.reuse.observed_new_tool_calls = replay.tools.length
    receipt.reuse.blocked_model_requests = replay.blocked_model_requests
    receipt.reuse.blocked_tool_calls = replay.blocked_tool_calls
  }
  receipt.status = 'passed'
} catch (error) {
  receipt.status = 'failed'
  receipt.error = error.stack
  throw error
} finally {
  if (browser) await browser.close()
  if (server.exitCode === null) {
    try { process.platform === 'win32' ? server.kill('SIGTERM') : process.kill(-server.pid, 'SIGTERM') } catch { /* already stopped */ }
  }
  let snapshot = JSON.stringify(receipt, (key, value) =>
    /^(?:apiKey|api_key|authorization|remoteAuthorization|accessToken|refreshToken|cookie|secret)$/i.test(key) ? '[REDACTED]' : value, 2) + '\n'
  if (process.env.DEEPSEEK_API_KEY) snapshot = snapshot.replaceAll(process.env.DEEPSEEK_API_KEY, '[REDACTED]')
  snapshot = snapshot.replace(/([?&]token=)[^&\s"<>]+/g, '$1[REDACTED]')
  await writeFile(output, snapshot)
  console.log(JSON.stringify({ status: receipt.status, receipt: output, mode: values.mode }))
}
