/** Metadata-only helpers and optional public demo skill provider for SDK validation. */
import { readFile } from 'node:fs/promises'
import { dirname } from 'node:path'

export const scientificNames = new Set(['acycle_analyze', 'acycle_swa', 'acycle_coco',
  'acycle_ecoco', 'acycle_interpolate_pro', 'acycle_tune', 'acycle_sensitivity', 'acycle_rerun'])

export function parseResultValues(message) {
  const values = []
  for (const block of message?.content ?? []) {
    if (block.type !== 'text') continue
    const text = block.text.trim()
    const candidates = [text]
    // v0.5 keeps the structured RunError JSON after the native tool error prefix.
    if (text.includes('{') && text.endsWith('}')) candidates.push(text.slice(text.indexOf('{')))
    for (const candidate of candidates) {
      try { values.push(JSON.parse(candidate)); break } catch { /* prose is not a result object */ }
    }
  }
  return values
}

export function scientificOutcome(turn) {
  const completed = new Map(), failures = []
  let calls = 0
  const walk = value => {
    if (!value || typeof value !== 'object') return
    if (value.run_id && value.status === 'completed') completed.set(value.run_id, {
      run_id: value.run_id, operation: value.operation, parent_run_id: value.parent_run_id,
      input_sha256: value.input_sha256, output_dir: value.output_dir,
    })
    if (Array.isArray(value)) value.forEach(walk)
    else for (const [key, child] of Object.entries(value)) {
      if (key === 'runs' || key === 'run' || key === 'result') walk(child)
    }
  }
  for (const call of turn.tool_calls ?? []) {
    if (!scientificNames.has(call.name)) continue
    calls++
    const result = (turn.tool_results ?? []).find(result => {
      const message = result.message ?? {}
      return (message.toolCallId ?? message.callId ?? message.source?.callId) === call.callId
    })
    if (!result) continue
    const values = parseResultValues(result.message)
    const structured = values.find(value => value && typeof value === 'object' &&
      (value.status === 'failed' || value.status === 'error' || value.error))
    if (result.message?.isError || structured) failures.push({
      tool: call.name, call_id: call.callId,
      structured_failure: structured ?? null,
      text: (result.message?.content ?? []).filter(block => block.type === 'text').map(block => block.text).join('\n'),
    })
    else values.forEach(walk)
  }
  return { scientific_calls: calls, completed_runs: [...completed.values()], failures }
}

export function turnExecutionPolicy(turn, { maxScientificCalls, maxToolCalls } = {}) {
  const supplied = turn.execution_policy ?? {}
  const policy = {
    kind: supplied.kind ?? 'scientific',
    minimum_completed_runs: supplied.min_completed_scientific_runs ?? 1,
    maximum_scientific_calls: Number(maxScientificCalls ?? supplied.max_scientific_calls ?? 2),
    maximum_tool_calls: Number(maxToolCalls ?? supplied.max_tool_calls ?? (supplied.max_scientific_calls > 2 ? 70 : 24)),
  }
  if (policy.kind === 'read_only') { policy.minimum_completed_runs = 0; policy.maximum_scientific_calls = 0 }
  for (const key of ['minimum_completed_runs', 'maximum_scientific_calls', 'maximum_tool_calls']) {
    if (!Number.isSafeInteger(policy[key]) || policy[key] < 0) throw new Error(`Invalid execution policy: ${key}`)
  }
  if (policy.minimum_completed_runs > policy.maximum_scientific_calls) throw new Error('The scientific-call budget is smaller than the declared minimum completed runs')
  return policy
}

export async function loadPublicSkill(path) {
  const raw = await readFile(path, 'utf8')
  const name = raw.match(/^name:\s*["']?([a-z0-9-]+)["']?\s*$/m)?.[1]
  const description = raw.match(/^description:\s*(.+)$/m)?.[1]?.replace(/^['"]|['"]$/g, '')
  if (!name || !description) throw new Error(`Missing public skill name/description: ${path}`)
  return { name, description, path, raw, content: raw.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '') }
}

// Mounted only when the scenario explicitly declares its public demo skill.
export const name = 'acycle-public-demo-skill'
export const inject = ['skills']
export async function apply(ctx, config) {
  const skill = await loadPublicSkill(config.skillPath)
  const definition = { name: skill.name, description: skill.description, content: skill.content,
    path: skill.path, source: 'bundled', provider: name,
    invocation: { modelInvocable: true, userInvocable: true },
    resourceBase: { kind: 'directory', path: dirname(skill.path) } }
  ctx.skills.registerProvider(() => ({
    name,
    list: async () => [{ ...definition, content: undefined, rank: 600, locator: definition.name }],
    get: async candidate => candidate.name === definition.name ? definition : undefined,
  }))
}
