#!/usr/bin/env node
/** Real multi-user-turn tests through the published Harness SDK/profile/AgentLoop.
 * User text and expected outcomes live separately in the scenario manifest.
 * No expected tool names, arguments or scientific outcomes are inserted into live prompts.
 */
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import { readFile, writeFile, mkdir, access, rename, appendFile } from 'node:fs/promises'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'
import { scientificNames, scientificOutcome, turnExecutionPolicy, loadPublicSkill, inheritRecordedCatalog } from './harness_conversation_support.mjs'

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const { values } = parseArgs({ options: {
  runtime: { type: 'string', default: '/workspace/harness-conversation-runtime' },
  scenarios: { type: 'string', default: join(repository, 'tests/fixtures/conversation_scenarios.json') },
  case: { type: 'string' },
  output: { type: 'string' },
  workspace: { type: 'string' },
  plugin: { type: 'string', default: join(repository, 'plugin/index.mjs') },
  mode: { type: 'string', default: 'live' },
  model: { type: 'string', default: 'deepseek-flash' },
  'turn-timeout-seconds': { type: 'string', default: '2400' },
  'max-tool-calls': { type: 'string' },
  'max-scientific-calls': { type: 'string' },
  'max-user-turns': { type: 'string' },
  'expect-acycle-tools': { type: 'string' },
  'expect-acycle-skills': { type: 'string' },
  resume: { type: 'string' },
  continue: { type: 'string' },
  'answer-topic': { type: 'string' },
  'initialize-only': { type: 'boolean', default: false },
} })
if (!['live', 'mock'].includes(values.mode)) throw new Error('--mode must be live or mock')
if (values.mode === 'live' && !process.env.DEEPSEEK_API_KEY) throw new Error('Set DEEPSEEK_API_KEY in the launching environment')
const runtimeRoot = resolve(values.runtime)
const require = createRequire(join(runtimeRoot, 'package.json'))
const load = async name => import(pathToFileURL(require.resolve(name)).href)
const { DeepSeekHarness } = await load('@deepseek-ai/dsh-sdk-client')
const { Context } = await load('@deepseek-ai/cordis')
const { default: AttachmentStore } = await load('@deepseek-ai/dsh-attachment-local')
const scenarioPath = resolve(values.scenarios)
const scenarioRoot = dirname(scenarioPath)
const scenarioBytes = await readFile(scenarioPath)
const declaredManifest = JSON.parse(scenarioBytes.toString('utf8'))
const publicManifestPath = declaredManifest.manifest_path ? resolve(scenarioRoot, declaredManifest.manifest_path) : null
const publicManifestBytes = publicManifestPath ? await readFile(publicManifestPath) : null
const publicManifest = publicManifestBytes ? JSON.parse(publicManifestBytes.toString('utf8')) : null
const publicSkill = declaredManifest.skill_path ? await loadPublicSkill(resolve(scenarioRoot, declaredManifest.skill_path)) : null
if (publicSkill && !publicManifest) throw new Error('A preset-assisted scenario must declare both skill_path and manifest_path')
const publicSourcesPath = publicManifest ? join(dirname(publicManifestPath), 'SOURCES.md') : null
const publicSourcesBytes = publicSourcesPath ? await readFile(publicSourcesPath) : null
const manifest = values.mode === 'mock' ? { cases: [{
  id: 'keyless-sdk-infrastructure',
  attachment: { root: 'repository', path: 'benchmarks/data/weedon_2020_lavernock_0_13_17m.csv', name: 'observations.csv' },
  turns: [{ user_prompt: '请接收附件并检查分析环境。' }, { user_prompt: '保留刚才的文件，确认我们仍在同一会话。' }],
}] } : declaredManifest
const scenario = manifest.cases.find(item => item.id === values.case) ?? (values.mode === 'mock' ? manifest.cases[0] : null)
if (!scenario) throw new Error('Provide --case naming a scenario manifest entry')
if (values.resume && values.continue) throw new Error('Use either --resume for clarification or --continue for the next planned user turn')
const previousPath = values.resume ?? values.continue
const previous = previousPath ? JSON.parse(await readFile(resolve(previousPath), 'utf8')) : null
if (previous && previous.case_id !== scenario.id) throw new Error('The previous receipt belongs to another scenario')
if (values.resume && previous.status !== 'needs_human_clarification') {
  throw new Error('--resume requires a needs_human_clarification receipt from the same case')
}
if (values.continue && previous.status !== 'completed') throw new Error('--continue requires a completed previous transport attempt')
const answer = values['answer-topic'] ? scenario.clarification_answers?.[values['answer-topic']] : null
if (values.resume && !answer) throw new Error('Choose --answer-topic from this scenario\'s predeclared user facts')
if (values.resume && previous.turns.filter(turn => turn.clarification_topic).length >= 2) {
  throw new Error('The predeclared maximum of two clarification turns has been reached')
}
if (!values.resume && values['answer-topic']) throw new Error('--answer-topic requires --resume')
const output = resolve(values.output ?? join(repository, 'validation/harness-conversations', `${scenario.id}.json`))
const workspace = resolve(values.workspace ?? previous?.workspace ?? join(dirname(output), `${scenario.id}-workspace`))
if (previous && workspace !== previous.workspace) throw new Error('A resumed conversation must keep its original workspace')
const dshHome = join(workspace, '.harness-home')
if (!previous) {
  try { await access(dshHome); throw new Error('A new case requires a fresh workspace without an existing .harness-home') }
  catch (error) { if (error.code !== 'ENOENT') throw error }
}
await mkdir(workspace, { recursive: true })
await mkdir(dirname(output), { recursive: true })
try { await access(output); throw new Error(`Refusing to overwrite an existing conversation receipt: ${output}`) }
catch (error) { if (error.code !== 'ENOENT') throw error }
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
if (previous?.scenario_sha256 && previous.scenario_sha256 !== hash(scenarioBytes)) throw new Error('Scenario changed since this Session started; use a new Session')
const pluginSha = hash(await readFile(resolve(values.plugin)))
if (previous && previous.runtime.plugin_sha256 !== pluginSha) throw new Error('Plugin changed since this Session started; preserve the prior receipt and start a new Session')
const previousCatalog = previous ? await inheritRecordedCatalog(previous, resolve(previousPath), {
  provider: values.mode === 'live' ? 'deepseek-official' : 'acycle-fixture',
  model: values.mode === 'live' ? values.model : 'fixture',
}) : {}
const packageVersion = name => JSON.parse(require('node:fs').readFileSync(require.resolve(name + '/package.json'), 'utf8')).version
const artifactContext = new Context()
const attachments = new AttachmentStore(artifactContext, { dshHome })
const fixtureKind = scenario.attachment.root ?? (publicManifest ? 'scenario' : 'repository')
const fixtureRoot = fixtureKind === 'acycle' ? process.env.ACYCLE_ROOT : fixtureKind === 'scenario' ? scenarioRoot : repository
if (!fixtureRoot) throw new Error('Set ACYCLE_ROOT for this official Acycle fixture')
const source = resolve(fixtureRoot, scenario.attachment.path)
const bytes = await readFile(source)
const fixtureSha = scenario.attachment.sha256 ?? (values.mode === 'live' ? publicManifest?.input?.sha256 : null)
if (fixtureSha && hash(bytes) !== fixtureSha) {
  throw new Error('Fixture bytes do not match the predeclared SHA256')
}
const ref = await attachments.saveFile({ data: bytes, name: scenario.attachment.name })
await artifactContext.fiber.dispose()
const pluginUrl = name => pathToFileURL(require.resolve(name)).href
const patch = [
  { id: 'agent-loop', config: { agents: [], maxParallelToolCalls: 1 } },
  { id: 'system-prompt', config: { personaPrefix: 'You are a scientific analysis assistant. Use relevant installed skills and available tools to help the user. All Acycle scientific calculations and plots must execute through MATLAB. Preserve original data and earlier results. Ask for scientific context that cannot be established from the supplied material. Explain actual results and limitations without inventing findings.' } },
  { id: 'llm-deepseek', config: { streamIdleTimeoutMs: 180000, retryPolicy: { mode: 'normal', maxRetries: 1 } } },
  { insert: [
    { id: 'acycle-skills', name: pluginUrl('@deepseek-ai/dsh-skill') },
    { id: 'acycle-tool-skill', name: pluginUrl('@deepseek-ai/dsh-tool-skill') },
    { id: 'acycle-session-query', name: pluginUrl('@deepseek-ai/dsh-session-query-sqlite'), config: { path: join(dshHome, 'query.db'), openAt: 'never' } },
    { id: 'acycle-present', name: pluginUrl('@deepseek-ai/dsh-tool-present'), config: { maxFiles: 30 } },
    { id: 'acycle-matlab', name: pathToFileURL(resolve(values.plugin)).href, config: { python: process.env.ACYCLE_PYTHON ?? 'python3' } },
  ] },
]
if (publicSkill) patch.push({ insert: [{ id: 'acycle-public-demo-skill',
  name: pathToFileURL(join(repository, 'scripts/harness_conversation_support.mjs')).href,
  config: { skillPath: publicSkill.path } }] })
if (values.mode === 'mock') {
  patch.push({ id: 'llm-deepseek', disabled: true })
  patch.push({ insert: [{ id: 'acycle-fixture', name: pathToFileURL(join(repository, 'scripts/harness_conversation_mock.mjs')).href, config: { runtimeRoot, skillName: publicSkill?.name, initialStep: previous ? 4 : 0 } }] })
}
const patchFile = join(workspace, 'conversation.patch.yml')
// JSON is a YAML subset. No credential is written to this profile patch.
await writeFile(patchFile, JSON.stringify(patch, null, 2) + '\n')
const secret = process.env.DEEPSEEK_API_KEY
const redact = value => {
  const text = JSON.stringify(value, null, 2)
  return secret ? text.replaceAll(secret, '[REDACTED]') : text
}
const receipt = {
  schema_version: 2, case_id: scenario.id, status: 'running', mode: values.mode,
  scenario_path: scenarioPath, scenario_sha256: hash(scenarioBytes),
  autonomy_class: values.mode === 'mock' ? 'scripted-infrastructure-only' : publicSkill ? 'preset-assisted' : 'unprescribed-user-goal',
  preset_assistance: publicSkill ? {
    public_skill: { name: publicSkill.name, path: publicSkill.path, sha256: hash(publicSkill.raw) },
    public_manifest: { path: publicManifestPath, sha256: hash(publicManifestBytes) },
    public_sources: { path: publicSourcesPath, sha256: hash(publicSourcesBytes) },
    disclosure: 'The public demo skill and scientific priors are model-visible. This is not blind method selection. Scenario acceptance and execution budgets are not injected into model messages.',
  } : null,
  scope: values.mode === 'live' ? 'Published official Harness SDK, sdk-minimal profile, AgentLoop, skills, durable file attachment and multiple independent user turns with a real DeepSeek provider. No desktop browser UI assertion.' : 'Keyless infrastructure fixture only; no real model or scientific execution.',
  started_at_utc: new Date().toISOString(), runtime: {
    ...previousCatalog,
    sdk_client: packageVersion('@deepseek-ai/dsh-sdk-client'), dsh: packageVersion('@deepseek-ai/dsh'),
    profile: 'sdk-minimal', model: values.mode === 'live' ? values.model : 'fixture',
    plugin_path: resolve(values.plugin), plugin_sha256: pluginSha,
  }, workspace, dsh_home: dshHome,
  attachment: { source_file: source, sha256: hash(bytes), bytes: bytes.length, ref },
  prompt_policy: 'Only scenario user_prompt strings and the uploaded FileBlock are supplied as user input; acceptance and execution_policy fields are never model-visible. A declared public demo skill and its public files are registered separately and disclosed in preset_assistance.',
  turns: previous?.turns ?? [], errors: [],
  ...(previous ? { resumed_from: resolve(previousPath), resumed_session_id: previous.session_id } : {}),
}
let checkpointQueue = Promise.resolve()
const checkpoint = () => {
  const snapshot = redact(receipt) + '\n'
  checkpointQueue = checkpointQueue.then(async () => {
    const temporary = `${output}.tmp`
    await writeFile(temporary, snapshot)
    await rename(temporary, output)
  })
  return checkpointQueue
}
await checkpoint()
const childEnv = { ...process.env, ACYCLE_WORKSPACE: workspace }
if (values.mode === 'mock') delete childEnv.DEEPSEEK_API_KEY
const harness = new DeepSeekHarness({
  dshHome, profile: 'sdk-minimal', patches: [patchFile], processCwd: workspace, cwd: workspace,
  provider: values.mode === 'live' ? 'deepseek-official' : 'acycle-fixture',
  model: values.mode === 'live' ? values.model : 'fixture', maxTokens: 8192,
  initializeTimeoutMs: 120000, requestTimeoutMs: Number(values['turn-timeout-seconds']) * 1000 + 30000, env: childEnv,
})
let closing = false
let completed = true
const abortRuntime = async reason => {
  if (closing) return
  closing = true
  receipt.errors.push(reason)
  await checkpoint()
  await harness.close()
}
const onSigint = () => { void abortRuntime('Runner interrupted with SIGINT; retain this incomplete attempt') }
const onSigterm = () => { void abortRuntime('Runner interrupted with SIGTERM; retain this incomplete attempt') }
process.on('SIGINT', onSigint)
process.on('SIGTERM', onSigterm)
try {
  await harness.start()
  receipt.initialized = true
  // A named session() handle does not restore persisted runtime state. The
  // published SDK requires resumeSession() before sending a new user message.
  const session = previous ? await harness.resumeSession(previous.session_id) : harness.session()
  receipt.session_id = session.id
  await checkpoint()
  if (!values['initialize-only']) {
    const pendingIndex = previous?.pending_scenario_turn_index
    const nextIndex = previous?.next_scenario_turn_index ?? (previous ? Math.max(...previous.turns.map(turn => turn.scenario_turn_index ?? turn.index)) + 1 : 0)
    const remainingTurns = values.resume ? [
      { ...scenario.turns[pendingIndex], user_prompt: answer, scenario_index: pendingIndex, clarification_topic: values['answer-topic'] },
      ...scenario.turns.slice(pendingIndex + 1).map((turn, offset) => ({ ...turn, scenario_index: pendingIndex + 1 + offset })),
    ] : scenario.turns.slice(nextIndex).map((turn, offset) => ({ ...turn, scenario_index: nextIndex + offset }))
    const turnLimit = values['max-user-turns'] === undefined ? remainingTurns.length : Number(values['max-user-turns'])
    if (!Number.isSafeInteger(turnLimit) || turnLimit < 1) throw new Error('--max-user-turns must be a positive integer')
    const turnQueue = remainingTurns.slice(0, turnLimit)
    if (!turnQueue.length) throw new Error('No planned user turns remain in this Session')
    receipt.selected_user_turns_this_invocation = turnQueue.map(turn => turn.scenario_index)
    for (const turn of turnQueue) {
      const index = receipt.turns.length
      const started = Date.now()
      const policy = turnExecutionPolicy(turn, { maxScientificCalls: values['max-scientific-calls'], maxToolCalls: values['max-tool-calls'] })
      const entry = { index, scenario_turn_id: turn.id, scenario_turn_index: turn.scenario_index, clarification_topic: turn.clarification_topic, user_prompt: turn.user_prompt, execution_policy: policy, started_at_utc: new Date().toISOString(), tool_calls: [], tool_results: [], emitted_images: [], emitted_files: [], notifications_count: 0 }
      receipt.turns.push(entry)
      await checkpoint()
      const input = [{ type: 'text', text: turn.user_prompt }]
      if (index === 0) input.push({ type: 'file', attachment: ref })
      let failure
      const timer = setTimeout(() => { failure = `User turn ${index + 1} exceeded the configured time bound`; void abortRuntime(failure) }, Number(values['turn-timeout-seconds']) * 1000)
      timer.unref()
      const eventPath = join(dirname(output), `${basename(output, '.json')}.turn-${index + 1}.json`)
      entry.event_log = eventPath.replace(/\.json$/, '.events.jsonl')
      let eventQueue = Promise.resolve()
      try {
        const result = await session.run(input, { onNotification(notification) {
          eventQueue = eventQueue.then(() => appendFile(entry.event_log, redact(notification).replaceAll('\n', '') + '\n'))
          entry.notifications_count++
          if (notification.method !== 'session.event') return
          const event = notification.params.event
          if (event.type === 'request/header') {
            receipt.runtime.actual_model = event.data.header?.config
            receipt.runtime.model_visible_tool_names = (event.data.header?.tools ?? []).map(tool => tool.name ?? tool.function?.name).filter(Boolean).sort()
            receipt.runtime.catalog_evidence ??= {}
            receipt.runtime.catalog_evidence.tools = { source: 'current_session_event', session_id: receipt.session_id, event_seq: event.seq }
          }
          if (event.type === 'user/message' && event.data.source?.kind === 'skill-catalog') {
            receipt.runtime.model_visible_skill_names = (event.data.source.entries ?? []).map(skill => skill.name).sort()
            receipt.runtime.catalog_evidence ??= {}
            receipt.runtime.catalog_evidence.skills = { source: 'current_session_event', session_id: receipt.session_id, event_seq: event.seq }
          }
          if (event.type === 'tool/call') {
            entry.tool_calls.push({ ...event.data, event_seq: event.seq })
            process.stdout.write(JSON.stringify({ event: 'tool_call', case: scenario.id, turn: index + 1, name: event.data.name }) + '\n')
            if (entry.tool_calls.length > policy.maximum_tool_calls) {
              failure = `User turn ${index + 1} exceeded the configured tool-call budget`
              void abortRuntime(failure)
            }
            const scientificCalls = entry.tool_calls.filter(call => scientificNames.has(call.name)).length
            if (scientificCalls > policy.maximum_scientific_calls) {
              failure = `User turn ${index + 1} exceeded the configured scientific-call budget`
              void abortRuntime(failure)
            }
            void checkpoint()
          }
          if (event.type === 'tool/result') {
            entry.tool_results.push(event.data)
            for (const block of event.data.message?.content ?? []) {
              if (block.type === 'image') entry.emitted_images.push(block)
              if (block.type === 'file') entry.emitted_files.push(block)
            }
          }
          if (event.type === 'turn/end') entry.terminal = event.data.reason
          // Checkpoints keep expensive MATLAB results available if a later provider request fails.
          if (event.type === 'tool/result' || event.type === 'turn/end') void checkpoint()
        } })
        if (failure) throw new Error(failure)
        entry.final_response = result.finalResponse
        entry.duration_seconds = (Date.now() - started) / 1000
        entry.events_file = eventPath
        entry.scientific_outcome = scientificOutcome(entry)
        receipt.next_scenario_turn_index = turn.scenario_index + 1
        await writeFile(eventPath, redact(result) + '\n')
        await checkpoint()
        process.stdout.write(JSON.stringify({ event: 'user_turn_completed', case: scenario.id, turn: index + 1, tools: entry.tool_calls.map(call => call.name), images: entry.emitted_images.length }) + '\n')
        for (const [option, list, prefix] of [
          ['expect-acycle-tools', receipt.runtime.model_visible_tool_names, 'acycle_'],
          ['expect-acycle-skills', receipt.runtime.model_visible_skill_names, 'acycle-'],
        ]) {
          if (values[option] !== undefined && (list ?? []).filter(name => name.startsWith(prefix)).length !== Number(values[option])) {
            throw new Error(`Actual model-visible catalog does not satisfy --${option} ${values[option]}`)
          }
        }
        if (publicSkill && !(receipt.runtime.model_visible_skill_names ?? []).includes(publicSkill.name)) {
          throw new Error('The public demo skill is absent from the actual model-visible skill catalog')
        }
        // Workflow metadata is a continuation guard, not a scientific pass rubric.
        // A completed run count cannot prove all requested products or correct interpretation.
        if (values.mode === 'live' && !scenario.stop_after_expected_clarification) {
          const outcome = entry.scientific_outcome
          const enough = outcome.completed_runs.length >= policy.minimum_completed_runs
          if (outcome.failures.length || !enough || (policy.kind === 'read_only' && outcome.scientific_calls)) {
            completed = false
            receipt.status = outcome.failures.length ? 'execution_failed' : outcome.scientific_calls ? 'workflow_incomplete' : 'needs_human_clarification'
            receipt.pending_scenario_turn_index = turn.scenario_index
            receipt.next_scenario_turn_index = turn.scenario_index
            await checkpoint()
            break
          }
        }
      } finally { clearTimeout(timer); await eventQueue }
    }
  }
  if (completed) receipt.status = 'completed'
  receipt.remaining_planned_user_turns = Math.max(0, scenario.turns.length - (receipt.next_scenario_turn_index ?? 0))
  receipt.workflow_completion_is_not_scientific_acceptance = true
  if (values.mode === 'mock' && !values['initialize-only']) {
    const results = receipt.turns.flatMap(turn => turn.tool_results)
    if (results.some(result => result.message?.isError)) throw new Error('Infrastructure fixture contains a failed official tool result')
    const imported = results.flatMap(result => result.message?.content ?? [])
      .filter(block => block.type === 'text')
      .map(block => { try { return JSON.parse(block.text) } catch { return null } })
      .find(value => value?.status === 'imported')
    if (imported?.source_session_id !== receipt.session_id || imported?.sha256 !== hash(bytes)) {
      throw new Error('Infrastructure fixture failed attachment session/hash checks')
    }
    const secondTurnChecked = receipt.turns[1]?.tool_calls.some(call => call.name === 'acycle_inspect') ?? false
    if (receipt.turns.length > 1 && !secondTurnChecked) {
      throw new Error('Infrastructure fixture failed cross-user-turn tool-history check')
    }
    receipt.infrastructure_assertions = {
      official_profile_and_agent_loop: true, skill_loaded_through_official_tool: true,
      attachment_imported_from_current_session: true, imported_bytes_sha256_matches: true,
      two_distinct_user_messages_retained: receipt.turns.length > 1, second_turn_reuses_prior_tool_result: secondTurnChecked,
      real_model_or_scientific_acceptance: false,
    }
  }
  receipt.acceptance = 'Not inferred from transport completion; evaluate the separate predeclared scientific and conversation criteria.'
} catch (error) {
  receipt.status = 'failed'
  receipt.errors.push(String(error?.stack ?? error))
} finally {
  try { await harness.close() } catch (error) { receipt.errors.push(`Shutdown: ${String(error)}`); receipt.status = 'failed' }
  process.off('SIGINT', onSigint)
  process.off('SIGTERM', onSigterm)
  receipt.finished_at_utc = new Date().toISOString()
  await checkpoint()
}
process.stdout.write(JSON.stringify({ status: receipt.status, case: scenario.id, mode: values.mode, user_turns: receipt.turns.length, receipt: output }) + '\n')
if (receipt.status !== 'completed') process.exitCode = 1
