/** Keyless inspection of a real agent mounted from the generated Web preset. */
import { createRequire } from 'node:module'
import { randomUUID, createHash } from 'node:crypto'
import { writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

export const name = 'acycle-agent-composition-probe'
export const inject = ['agents', 'agentPresets', 'agentDefaultModel', 'systemPrompt', 'skills', 'tools', 'llm']

export async function apply(ctx, config) {
  const require = createRequire(join(config.runtime, 'package.json'))
  const { assembleContextFor } = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-agent')).href)
  const { renderPrompt } = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-system-prompt')).href)
  const { LlmAdapter, createUserMessage } = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-llm')).href)
  let captured
  class CompositionFixture extends LlmAdapter {
    async * stream(options) {
      if (!captured || options.messages.some(message => message.source?.kind === 'skill-catalog')) captured = options
      const text = 'Keyless agent composition inspected; no API or science executed.'
      yield { type: 'block-start', index: 0, blockType: 'text' }
      yield { type: 'text-delta', index: 0, text }
      yield { type: 'block-end', index: 0, block: { type: 'text', text } }
      yield { type: 'finish', reason: { kind: 'stop' } }
    }
  }
  ctx.llm.registerAdapter(['acycle-composition-fixture'], new CompositionFixture())
  const report = { status: 'running', scope: 'Actual Web-profile agent composition; no model or MATLAB execution.',
    model_api_called: false, matlab_executed: false, actual_agent_created: false }
  const run = async () => {
    let handle, fixtureHandle
    try {
      const choice = ctx.agentDefaultModel.currentSelection()
      const preset = await ctx.agentPresets.resolve(config.preset)
      const model = await ctx.llm.resolveModelInfo(choice.provider, choice.model)
      handle = await ctx.agents.create({ sessionId: `session-${randomUUID()}`, meta: { cwd: config.workspace, agentPreset: preset.id },
        agentOptions: choice, setup: async agentCtx => { await ctx.agentPresets.mount(agentCtx, preset.id) } })
      const agent = handle.agent
      report.actual_agent_created = true
      const context = assembleContextFor(agent, new AbortController().signal)
      const assembly = await ctx.systemPrompt.assemble(context)
      const prompt = renderPrompt(assembly)
      const skills = await ctx.skills.list({ scope: context.scope, cwd: config.workspace })
      const acycleSkills = skills.filter(skill => skill.name.startsWith('acycle-'))
      const loaded = await ctx.skills.get('acycle-intake', { scope: context.scope, cwd: config.workspace })
      report.session_id = agent.id
      report.selected_preset = ctx.agentPresets.composedPreset(agent.ctx)
      report.model = { provider: choice.provider, id: choice.model, inputModalities: model.inputModalities,
        imagePixelBudget: model.imagePixelBudget, imageMaxBytes: model.imageMaxBytes }
      report.tools = assembly.tools.map(tool => tool.name ?? tool.function?.name)
      report.native_tool_count = report.tools.filter(name => name.startsWith('acycle_')).length
      report.skills = acycleSkills.map(skill => skill.name)
      report.skill_body_loaded = Boolean(loaded?.content)
      report.persona_present = prompt.includes('This is the Acycle research deployment.')
      const capability = await ctx.tools.execute({ callId: `composition-${randomUUID()}`,
        name: 'acycle_capabilities', arguments: {}, agent, signal: new AbortController().signal })
      if (capability.isError) throw new Error(`Scoped capabilities failed: ${JSON.stringify(capability)}`)
      report.capabilities = { version: capability.value.version, backend: capability.value.backend,
        python_numerical_fallback: capability.value.python_numerical_fallback }
      // Current Harness injects skills as a durable pre-step catalog, not a static system section.
      fixtureHandle = await ctx.agents.create({ sessionId: `session-${randomUUID()}`, meta: { cwd: config.workspace, agentPreset: preset.id },
        agentOptions: { provider: 'acycle-composition-fixture', model: 'keyless' },
        setup: async agentCtx => { await ctx.agentPresets.mount(agentCtx, preset.id) } })
      fixtureHandle.agent.followup(createUserMessage({ source: { kind: 'user' }, content: [
        { type: 'text', text: 'Inspect this deployment composition only. Do not call scientific tools.' }] }))
      await fixtureHandle.agent.whenIdle()
      const capturedText = JSON.stringify(captured?.messages ?? [])
      report.skills_in_model_messages = acycleSkills.every(skill => capturedText.includes(skill.name))
      report.catalog_transport = 'Actual preset AgentLoop request captured by a deterministic keyless adapter; official deployment route resolved separately.'
      report.fixture_request_captured = Boolean(captured)
      report.prompt_sha256 = createHash('sha256').update(prompt).digest('hex')
      report.prompt_sections = assembly.sections.map(section => section.name)
      report.compositions = ctx.agentPresets.inspectCompositions(agent.ctx)
      const failures = []
      if (report.selected_preset !== config.preset) failures.push('Actual agent selected a different preset')
      if (!report.persona_present) failures.push('Acycle persona absent from the actual agent prompt')
      if (!report.skills.length || !report.skills_in_model_messages || !report.skill_body_loaded || !captured) failures.push('Acycle skill catalog/body missing from the actual scoped model messages')
      if (!report.tools.includes('acycle_rerun') || !report.tools.includes('read_image') || !report.tools.includes('present')) failures.push('Native research/image/presentation tools absent in actual scope')
      if (report.native_tool_count !== config.expectedNativeTools) failures.push(`Expected ${config.expectedNativeTools} scoped native tools; found ${report.native_tool_count}`)
      if (report.skills.length !== config.expectedSkills) failures.push(`Expected ${config.expectedSkills} scoped Acycle skills; found ${report.skills.length}`)
      if (report.capabilities.version !== config.expectedVersion || report.capabilities.python_numerical_fallback !== false) failures.push('Actual native bridge capability/version mismatch')
      if (!model.inputModalities?.includes('image')) failures.push('Actual route does not resolve image capability')
      report.failures = failures
      report.status = failures.length ? 'failed' : 'passed'
      // The full assembled prompt is evidence; it contains no API key or scientific input.
      await writeFile(config.output + '.prompt.txt', prompt + '\n')
      await writeFile(config.output + '.request.json', JSON.stringify({ fixture: true, messages: captured?.messages ?? [] }, null, 2)+'\n')
    } catch (error) {
      report.status = 'failed'
      report.error = String(error?.stack ?? error)
    } finally {
      if (handle) await handle.dispose()
      if (fixtureHandle) await fixtureHandle.dispose()
      await writeFile(config.output, JSON.stringify(report, null, 2) + '\n')
    }
  }
  // All declarations must finish activation before a real agent can bind a preset.
  const timer = setTimeout(() => { void run() }, 1000)
  ctx.on('dispose', () => clearTimeout(timer))
}
