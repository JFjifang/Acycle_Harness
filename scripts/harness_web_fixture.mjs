/** Test-only Web observer and optional scripted adapter; never claims model autonomy. */
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { writeFile } from 'node:fs/promises'

export const name = 'acycle-web-acceptance-fixture'
export const inject = ['llm', 'tools', 'agents', 'skills']
const SCIENTIFIC = new Set(['acycle_analyze', 'acycle_swa', 'acycle_coco', 'acycle_ecoco',
  'acycle_rerun', 'acycle_sensitivity', 'acycle_interpolate_pro', 'acycle_tune'])

export async function apply(ctx, config) {
  const require = createRequire(join(config.runtime, 'package.json'))
  const { LlmAdapter } = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-llm')).href)
  const audit = { mode: config.mode, fixture_adapter: config.mode === 'fixture',
    scientific_calls: [], session_id: null, preset: null, headers: [], tools: [], image_results: [],
    final_text: '', completed: false }
  let writes = Promise.resolve()
  const save = () => {
    let snapshot = JSON.stringify(audit, (key, value) =>
      /^(?:apiKey|api_key|authorization|remoteAuthorization|accessToken|refreshToken|cookie|secret)$/i.test(key) ? '[REDACTED]' : value, 2) + '\n'
    if (process.env.DEEPSEEK_API_KEY) snapshot = snapshot.replaceAll(process.env.DEEPSEEK_API_KEY, '[REDACTED]')
    snapshot = snapshot.replace(/([?&]token=)[^&\s"<>]+/g, '$1[REDACTED]')
    writes = writes.then(() => writeFile(config.audit, snapshot))
    return writes
  }
  try { audit.deepseek_catalog = await ctx.llm.resolveModelInfo('deepseek-official', 'deepseek-flash') }
  catch (error) { audit.deepseek_catalog_error = error.message }
  if (config.mode === 'replay') ctx.on('llm/stream', () => { throw new Error('Browser replay forbids new model requests') })
  ctx.on('tools/pre-execute', (exec, next) => {
    if (SCIENTIFIC.has(exec.name)) {
      audit.scientific_calls.push(exec.name)
      return { kind: 'deny', reason: 'This UI acceptance test may inspect existing outputs only; scientific recalculation is disabled.' }
    }
    return next()
  })
  ctx.on('session/event', (session, event) => {
    audit.session_id = session.id
    audit.preset = session.header.agentPreset
    if (event.type === 'request/header') {
      const header = event.data.header
      audit.headers.push({ config: header.config, tool_names: header.tools?.map(tool => tool.name) })
    }
    if (event.type === 'system/message' || event.type === 'request/context') {
      const text = JSON.stringify(event.data)
      audit.acycle_persona ||= text.includes('Acycle research deployment')
      audit.acycle_workflow_policy ||= text.includes('Acycle research workflow')
      audit.skill_names_in_prompt = [...new Set([...(audit.skill_names_in_prompt ?? []), ...(text.match(/acycle-[a-z-]+/g) ?? [])])]
    }
    if (event.type === 'user/message' && event.data.source?.kind === 'skill-catalog') {
      audit.model_visible_skill_catalog = event.data.source.entries.map(entry => entry.name)
    }
    if (event.type === 'tool/call') audit.tools.push({ name: event.data.name, arguments: event.data.arguments })
    if (event.type === 'tool/result') {
      const message = event.data.message
      for (const block of message.content ?? []) if (block.type === 'image') {
        audit.image_results.push({ attachment: block.attachment, offloaded: block.offloaded === true })
      }
      if (message.isError) (audit.tool_errors ??= []).push(message.content)
    }
    if (event.type === 'assistant/message') {
      const text = event.data.message.content.filter(block => block.type === 'text').map(block => block.text).join('\n')
      if (text) audit.final_text = text
    }
    if (event.type === 'turn/end') {
      void ctx.skills.list({ scope: ctx.agents.get(session.id), cwd: session.header.cwd }).then(skills => {
        audit.actual_agent_skills = skills.map(skill => skill.name)
        audit.completed = true
        return save()
      })
    }
  })
  if (config.mode !== 'fixture') { await save(); return }
  class FixtureAdapter extends LlmAdapter {
    listModels(provider) { return Promise.resolve([{ provider, id: 'fixture-text', name: 'UI fixture (text only)', inputModalities: ['text'] }]) }
    resolveModel(provider, model) { return Promise.resolve({ provider, id: model, name: 'UI fixture (text only)', inputModalities: ['text'] }) }
    async * stream(options) {
      const toolText = options.messages.filter(message => message.role === 'tool')
        .flatMap(message => message.content ?? []).filter(block => block.type === 'text').map(block => block.text)
      let name, args
      if (!toolText.some(text => text.includes('<skill_content'))) { name = 'skill'; args = { name: 'acycle-mini-robot' } }
      else if (!toolText.some(text => text.includes('"presentation"'))) { name = 'acycle_get_run'; args = { run_id: config.runId } }
      if (name) {
        const id = `web-fixture-${name}`
        const argumentsText = JSON.stringify(args)
        yield { type: 'block-start', index: 0, blockType: 'tool-call', id, name }
        yield { type: 'tool-call-delta', index: 0, id, name, argumentsDelta: argumentsText }
        yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name, arguments: argumentsText } }
        yield { type: 'finish', reason: { kind: 'tool-calls' } }
        return
      }
      const run = toolText.map(text => { try { return JSON.parse(text) } catch { return null } })
        .find(value => value?.presentation)
      if (!run) throw new Error('The real existing-run tool produced no presentation')
      const text = `UI acceptance fixture using existing MATLAB results. This text-only scripted adapter does not inspect pixels or perform scientific calculations. Run: ${run.run_id}.\n\n${run.presentation.display_markdown}`
      yield { type: 'block-start', index: 0, blockType: 'text' }
      yield { type: 'text-delta', index: 0, text }
      yield { type: 'block-end', index: 0, block: { type: 'text', text } }
      yield { type: 'finish', reason: { kind: 'stop' } }
    }
  }
  ctx.llm.registerAdapter(['acycle-ui-fixture'], new FixtureAdapter())
  await save()
}
