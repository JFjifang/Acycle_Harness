/** Protocol integration, not a MATLAB/scientific oracle. Uses published official services. */
import assert from 'node:assert/strict'
import test from 'node:test'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import { mkdtemp, mkdir, writeFile, readFile, symlink, rm, readdir, chmod } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { createHash } from 'node:crypto'
import * as plugin from '../index.mjs'
import { attachOutputs, deliveryConfig, renderResult } from '../attachments.mjs'

const runtime = process.env.ACYCLE_HARNESS_RUNTIME
const official = { skip: runtime ? false : 'Set ACYCLE_HARNESS_RUNTIME to a published official Harness installation' }
const sha256 = data => createHash('sha256').update(data).digest('hex')
const runId = '20261025T000000Z-123456abcdef'
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAMAAAACCAYAAACddGYaAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAEUlEQVQImWNgZGL+D8MMyBwARq8GH+UMN/MAAAAASUVORK5CYII=', 'base64')
let number = 0

async function setup(t, { importLimit, withAttachments = true } = {}) {
  const require = createRequire(join(resolve(runtime), 'package.json'))
  const load = async name => import(pathToFileURL(require.resolve(name)).href)
  const [{ Context, Service }, { default: SystemPrompt }, { default: ToolRuntime },
    { default: SkillRegistry }, { default: SessionStore }, { default: SessionQuery },
    { default: AttachmentStore }, { default: SessionProjections }, { default: LocalFs },
    Present, { turnBoundaryProjectionDefinition }, { createScope }] = await Promise.all([
    load('@deepseek-ai/cordis'), load('@deepseek-ai/dsh-system-prompt'), load('@deepseek-ai/dsh-tools'),
    load('@deepseek-ai/dsh-skill'), load('@deepseek-ai/dsh-session'), load('@deepseek-ai/dsh-session-query-sqlite'),
    load('@deepseek-ai/dsh-attachment-local'), load('@deepseek-ai/dsh-session-projection'),
    load('@deepseek-ai/dsh-fs-local'), load('@deepseek-ai/dsh-tool-present'), load('@deepseek-ai/dsh-agent-loop'),
    load('@deepseek-ai/dsh-scope'),
  ])
  const root = await mkdtemp(join(tmpdir(), 'acycle-official-attachments-'))
  const workspace = join(root, 'study')
  await mkdir(workspace)
  const ctx = new Context()
  t.after(async () => { await ctx.fiber.dispose(); await rm(root, { recursive: true, force: true }) })
  class WorkingDirectory extends Service {
    constructor(inner) { super(inner, 'workingDirectory') }
    async ensure() { return workspace }
  }
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime, { mode: 'native' })
  await ctx.plugin(SkillRegistry)
  await ctx.plugin(SessionStore)
  await ctx.plugin(SessionQuery, { path: join(root, 'sessions.sqlite'), openAt: 'never' })
  await ctx.plugin(SessionProjections)
  ctx.sessionProjections.register(turnBoundaryProjectionDefinition)
  if (withAttachments) await ctx.plugin(AttachmentStore, { dshHome: join(root, 'dsh') })
  await ctx.plugin(LocalFs, { cwd: workspace })
  await ctx.plugin(WorkingDirectory)
  await ctx.plugin(Present, { maxFiles: 8 })
  const python = process.env.ACYCLE_PYTHON || 'python3'
  const pluginFiber = await ctx.plugin(plugin, { workspace, python, ...(importLimit ? { maxImportBytes: importLimit } : {}) })
  const session = ctx.sessions.create(`attachment-test-${++number}`, { meta: { cwd: workspace } })
  const agent = { id: session.id, session }
  const scope = createScope(ctx, agent)
  agent.ctx = scope.ctx
  session.append('turn/start', { turn: 1 })
  function message(refs, kind = 'user', target = session) {
    const id = `message-${++number}`
    target.append('user/message', { id, role: 'user', source: { kind },
      content: refs.map(attachment => ({ type: 'file', attachment })) }, { surfaceOp: 'append' })
    return id
  }
  function execute(name, args = {}, owner = agent) {
    return ctx.tools.execute({ name, arguments: args, agent: owner, callId: `call-${++number}`, signal: new AbortController().signal })
  }
  function anotherAgent() {
    const session = ctx.sessions.create(`attachment-test-${++number}`, { meta: { cwd: workspace } })
    const owner = { id: session.id, session }
    owner.ctx = createScope(ctx, owner).ctx
    return owner
  }
  return { ctx, agent, session, root, workspace, message, execute, pluginFiber, anotherAgent }
}

test('official SystemPrompt always includes Acycle workflow rules and removes them with the plugin', official, async t => {
  const f = await setup(t)
  for (const assemblyContext of [{}, { scope: f.agent }]) {
    const assembly = await f.ctx.systemPrompt.assemble(assemblyContext)
    const rules = assembly.sections.filter(section => section.name === 'acycle:research-workflow')
    assert.equal(rules.length, 1, 'visible without invoking a skill first')
    assert.match(rules[0].text, /original MATLAB implementation.*scientific quality assessment/)
    assert.match(rules[0].text, /coordinate units, geological age constraints, orbital targets/)
    assert.match(rules[0].text, /ask the user.*wait before starting scientific analysis/)
    assert.match(rules[0].text, /acycle_rerun.*parameter_patch/)
    assert.match(rules[0].text, /Do not alter authentication or execute gh auth/)
    assert.match(rules[0].text, /main Chat.*presentation\.display_markdown/)
    assert.match(rules[0].text, /model declares image input and read_image is available/)
    assert.match(rules[0].text, /Numerical verification, model visual review, and user-visible Chat display are separate checks/)
  }
  await f.pluginFiber.dispose()
  const disposed = await f.ctx.systemPrompt.assemble({ scope: f.agent })
  assert.equal(disposed.sections.some(section => section.name === 'acycle:research-workflow'), false)
})

test('official registry imports only current Session user refs, preserving bytes and source', official, async t => {
  const f = await setup(t)
  const data = Buffer.from('depth,value\r\n0,2\r\n1,3\r\n')
  const ref = await f.ctx.attachments.saveFile({ data, name: 'Newark 数据.csv' })
  const sourceId = f.message([ref])
  const result = await f.execute('acycle_import_attachment')
  assert.equal(result.isError, false, JSON.stringify(result))
  assert.equal(result.value.status, 'imported')
  assert.equal(result.value.sha256, sha256(data))
  assert.equal(result.value.original_name, ref.name)
  assert.equal(result.value.source_message_id, sourceId)
  assert.deepEqual(await readFile(result.value.input_path), data)
  assert.deepEqual(JSON.parse(await readFile(result.value.import_receipt, 'utf8')).attachment, ref)
  assert.equal(f.ctx.tools.schemas().filter(item => item.name.startsWith('acycle_')).length, 13)
  const repeat = await f.execute('acycle_import_attachment')
  assert.equal(repeat.isError, false)
  assert.equal(repeat.value.input_path, result.value.input_path, 'repeat import reuses the verified immutable copy')

  const secret = await f.ctx.attachments.saveFile({ data: Buffer.from('0,100\n1,200\n'), name: 'other.csv' })
  const foreign = f.ctx.sessions.create('foreign-session', { meta: { cwd: f.workspace } })
  f.message([secret], 'user', foreign)
  const rejected = await f.execute('acycle_import_attachment', { attachment_id: secret.attachmentId })
  assert.equal(rejected.isError, true)
  assert.match(JSON.stringify(rejected), /No matching user file attachment/)
  f.message([secret], 'internal')
  assert.equal((await f.execute('acycle_import_attachment', { attachment_id: secret.attachmentId })).isError, true,
    'an internal message cannot authorize imported user data')
})

test('multiple files require selection; official host paths auto-import for Python intake', official, async t => {
  const f = await setup(t)
  const refs = await Promise.all(['a.csv', 'b.csv'].map((name, index) =>
    f.ctx.attachments.saveFile({ data: Buffer.from(`0,${index}\n1,${index + 1}\n2,${index + 2}\n`), name })))
  f.message(refs)
  const choices = await f.execute('acycle_import_attachment')
  assert.equal(choices.value.status, 'selection_required')
  assert.equal(choices.value.attachments.length, 2)
  const chosen = await f.execute('acycle_import_attachment', { attachment_id: refs[1].attachmentId })
  assert.equal(chosen.value.original_name, 'b.csv')
  const inspected = await f.execute('acycle_inspect', { input_path: f.ctx.attachments.fileHostPath(refs[0]) })
  assert.equal(inspected.isError, false, JSON.stringify(inspected))
  assert.equal(inspected.value.imported_attachment.original_name, 'a.csv')
  assert.equal(inspected.value.imported_attachment.sha256, refs[0].attachmentId.replace(/^sha256:/, ''))
  const guessedForeign = join(f.root, 'not-authorized.csv')
  await writeFile(guessedForeign, '0,4\n1,5\n2,6\n')
  const denied = await f.execute('acycle_inspect', { input_path: guessedForeign })
  assert.equal(denied.isError, true, 'external path remains under Python workspace restrictions')
})

test('official short handles resolve only unique current Session refs, with real prefix collisions requiring selection', official, async t => {
  const f = await setup(t)
  const ref = await f.ctx.attachments.saveFile({ data: Buffer.from('0,2\n1,3\n'), name: 'single.csv' })
  f.message([ref])
  for (const handle of [ref.attachmentId.slice(7, 15), ref.attachmentId.slice(0, 15)]) {
    const result = await f.execute('acycle_import_attachment', { attachment_id: handle })
    assert.equal(result.isError, false, JSON.stringify(result))
    assert.equal(result.value.attachment.attachmentId, ref.attachmentId)
  }
  // These distinct byte sequences share the actual SHA-256 prefix 53713352.
  const refs = await Promise.all([5191, 7079].map(value => f.ctx.attachments.saveFile({
    data: Buffer.from(`0,${value}\n1,2\n`), name: `collision-${value}.csv`,
  })))
  assert.notEqual(refs[0].attachmentId, refs[1].attachmentId)
  assert.equal(refs[0].attachmentId.slice(7, 15), '53713352')
  assert.equal(refs[1].attachmentId.slice(7, 15), '53713352')
  const other = f.anotherAgent()
  f.message([refs[1]], 'user', other.session)
  const foreign = await f.execute('acycle_import_attachment', { attachment_id: '53713352' })
  assert.equal(foreign.isError, true, 'a short handle cannot reach another Session attachment')
  f.message(refs)
  const ambiguous = await f.execute('acycle_import_attachment', { attachment_id: 'sha256:53713352' })
  assert.equal(ambiguous.isError, false)
  assert.equal(ambiguous.value.status, 'selection_required')
  assert.deepEqual(ambiguous.value.attachments.map(item => item.attachmentId), refs.map(item => item.attachmentId))
  const selected = await f.execute('acycle_import_attachment', { attachment_id: refs[0].attachmentId })
  assert.equal(selected.isError, false)
  assert.equal(await readFile(selected.value.input_path, 'utf8'), '0,5191\n1,2\n')
})

test('bare filenames prefer current uploads, preserve explicit workspace paths, and reject ambiguous uploads', official, async t => {
  const f = await setup(t)
  const local = join(f.workspace, 'input.csv')
  const oldData = Buffer.from('0,90\n1,91\n')
  await writeFile(local, oldData)
  const ref = await f.ctx.attachments.saveFile({ data: Buffer.from('0,2\n1,3\n'), name: 'input.csv' })
  f.message([ref])
  const bare = await f.execute('acycle_inspect', { input_path: 'input.csv' })
  assert.equal(bare.isError, false, JSON.stringify(bare))
  assert.equal(bare.value.imported_attachment.attachment.attachmentId, ref.attachmentId)
  assert.equal(bare.value.sha256, ref.attachmentId.slice(7))
  for (const input_path of ['./input.csv', local]) {
    const explicit = await f.execute('acycle_inspect', { input_path })
    assert.equal(explicit.isError, false)
    assert.equal(explicit.value.sha256, sha256(oldData))
    assert.equal(explicit.value.imported_attachment, undefined)
  }
  await writeFile(join(f.workspace, 'local-only.csv'), oldData)
  const fallback = await f.execute('acycle_inspect', { input_path: 'local-only.csv' })
  assert.equal(fallback.isError, false)
  assert.equal(fallback.value.sha256, sha256(oldData))
  const different = await f.ctx.attachments.saveFile({ data: Buffer.from('0,4\n1,5\n'), name: 'input.csv' })
  f.message([different])
  const ambiguous = await f.execute('acycle_inspect', { input_path: 'input.csv' })
  assert.equal(ambiguous.isError, true)
  assert.match(JSON.stringify(ambiguous), /Multiple Session attachments match/)
  assert.deepEqual(await readFile(local), oldData, 'workspace data was not changed')
})

test('every import preserves its own source receipt across messages and Sessions without changing prior records', official, async t => {
  const f = await setup(t)
  const data = Buffer.from('0,2\n1,3\n')
  const ref = await f.ctx.attachments.saveFile({ data, name: 'input.csv' })
  const firstMessage = f.message([ref])
  const first = await f.execute('acycle_import_attachment')
  assert.equal(first.isError, false)
  const originalReceipt = await readFile(first.value.import_receipt)
  const legacyReceipt = first.value.input_path + '.source.json'
  await writeFile(legacyReceipt, originalReceipt)
  const secondMessage = f.message([ref])
  const second = await f.execute('acycle_import_attachment')
  const other = f.anotherAgent()
  const thirdMessage = f.message([ref], 'user', other.session)
  const third = await f.execute('acycle_import_attachment', {}, other)
  const results = [first, second, third]
  assert.ok(results.every(result => !result.isError), JSON.stringify(results))
  assert.equal(new Set(results.map(result => result.value.import_receipt)).size, 3)
  assert.equal(new Set(results.map(result => result.value.input_path)).size, 1)
  for (const [index, result] of results.entries()) {
    const receipt = JSON.parse(await readFile(result.value.import_receipt, 'utf8'))
    assert.deepEqual(receipt, result.value)
    assert.equal(receipt.source_message_id, [firstMessage, secondMessage, thirdMessage][index])
    assert.equal(receipt.source_session_id, index === 2 ? other.id : f.agent.id)
  }
  assert.deepEqual(await readFile(first.value.import_receipt), originalReceipt)
  assert.deepEqual(await readFile(legacyReceipt), originalReceipt)
  assert.deepEqual(await readFile(first.value.input_path), data)
})

test('import rejects byte limits and a symlinked destination, leaving source intact', official, async t => {
  const f = await setup(t, { importLimit: 12 })
  const data = Buffer.from('0,2\n1,3\n')
  const ref = await f.ctx.attachments.saveFile({ data, name: 'input.csv' })
  f.message([ref])
  const outside = join(f.root, 'outside')
  await mkdir(outside)
  await symlink(outside, join(f.workspace, '.acycle'))
  const rejected = await f.execute('acycle_import_attachment')
  assert.equal(rejected.isError, true)
  assert.match(JSON.stringify(rejected), /real directories inside the workspace/)
  assert.deepEqual(await readdir(outside), [])
  assert.deepEqual(await readFile(f.ctx.attachments.fileHostPath(ref)), data)
  const big = await f.ctx.attachments.saveFile({ data: Buffer.from('0,2\n1,3\n2,4\n3,5\n'), name: 'big.csv' })
  f.message([big])
  const overLimit = await f.execute('acycle_import_attachment')
  assert.equal(overLimit.isError, true)
  assert.match(JSON.stringify(overLimit), /import byte limit/)
})

test('official sha256 refs detect altered source bytes and remove partial imports', official, async t => {
  const f = await setup(t)
  const ref = await f.ctx.attachments.saveFile({ data: Buffer.from('0,2\n1,3\n'), name: 'input.csv' })
  f.message([ref])
  const path = f.ctx.attachments.fileHostPath(ref)
  await chmod(path, 0o600)
  await writeFile(path, '0,8\n1,9\n')
  const result = await f.execute('acycle_import_attachment')
  assert.equal(result.isError, true)
  assert.match(JSON.stringify(result), /integrity verification|digest does not match/)
  assert.deepEqual(await readdir(join(f.workspace, '.acycle', 'imports')), [], 'temporary file removed on rejection')
})

test('official image/file refs and present deliver both spectrum and evolution with original bytes', official, async t => {
  const f = await setup(t)
  const output = join(f.workspace, '.acycle', 'runs', runId, 'outputs')
  await mkdir(output, { recursive: true })
  const artifacts = {}
  for (const name of ['preprocessing', 'spectrum', 'evolution']) {
    artifacts[name] = join(output, `${name}.png`)
    await writeFile(artifacts[name], png)
  }
  artifacts.mat = join(output, 'results.mat')
  artifacts.csv = join(output, 'spectrum.csv')
  artifacts.fig = join(output, 'spectrum.fig')
  await writeFile(artifacts.mat, 'Protocol test fixture: not a scientific MAT result')
  await writeFile(artifacts.csv, 'frequency,power\n1,2\n')
  await writeFile(artifacts.fig, 'Protocol test fixture: not a scientific FIG result')
  f.ctx.tools.register({ name: 'fixture_delivery', description: 'Test saved-artifact delivery only', parameters: {},
    output: { schema: { type: 'object', additionalProperties: true }, render: renderResult },
    execute: async (_args, exec) => attachOutputs(f.ctx, { status: 'complete', run_id: runId, artifacts }, f.workspace, exec, deliveryConfig()),
  })
  const result = await f.execute('fixture_delivery')
  assert.equal(result.isError, false, JSON.stringify(result))
  assert.equal(result.value.presentation.status, 'available', JSON.stringify(result.value.presentation))
  assert.equal(result.value.presentation.delivery.status, 'presented')
  const events = f.session.snapshotEvents().filter(event => event.type === 'deliverables/presented')
  assert.equal(events.length, 1)
  const paths = events[0].data.files.map(file => file.path)
  assert.ok(paths.includes(artifacts.spectrum), 'spectrum is a real official deliverable')
  assert.ok(paths.includes(artifacts.evolution), 'EvoFFT is a real official deliverable')
  assert.ok(paths.includes(artifacts.mat), 'raw MAT is available as a deliverable')
  assert.ok(result.content.filter(block => block.type === 'image').every(block => block.offloaded === true))
  assert.equal(result.content.filter(block => block.type === 'file').length, 6)
  for (const item of result.value.presentation.files) {
    assert.deepEqual(await readFile(f.ctx.attachments.fileHostPath(item.attachment)), await readFile(item.path))
  }
})

test('path intake remains usable without attachments; attachment import gives an actionable error', official, async t => {
  const f = await setup(t, { withAttachments: false })
  const input = join(f.workspace, 'local.csv')
  await writeFile(input, '0,2\n1,3\n2,5\n')
  const result = await f.execute('acycle_inspect', { input_path: input })
  assert.equal(result.isError, false, JSON.stringify(result))
  const missing = await f.execute('acycle_import_attachment')
  assert.equal(missing.isError, true)
  assert.match(JSON.stringify(missing), /attachments and sessionQuery services/)
})
