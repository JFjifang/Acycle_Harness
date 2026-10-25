#!/usr/bin/env node
/** Keyless official-SDK continuation across two exited OS processes, not live-model acceptance. */
import { execFileSync } from 'node:child_process'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'
import assert from 'node:assert/strict'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const { values } = parseArgs({ options: {
  runtime: { type: 'string', default: '/workspace/harness-conversation-runtime' },
  output: { type: 'string' }, workspace: { type: 'string' },
  plugin: { type: 'string', default: join(root, 'plugin/index.mjs') },
} })
if (!values.output || !values.workspace) throw new Error('Provide a fresh --workspace and --output directory')
const output = resolve(values.output), workspace = resolve(values.workspace)
await mkdir(output, { recursive: true })
const files = ['first-process.json', 'second-process.json'].map(name => join(output, name))
const common = [join(root, 'scripts/harness_conversation.mjs'), '--mode', 'mock',
  '--runtime', resolve(values.runtime), '--scenarios', join(root, 'demo/newark-0.5.0/scenarios.json'),
  '--workspace', workspace, '--plugin', resolve(values.plugin), '--max-user-turns', '1',
  '--expect-acycle-tools', '13', '--expect-acycle-skills', '10']
const env = { ...process.env }
delete env.DEEPSEEK_API_KEY
const processEvidence = []
for (let index = 0; index < 2; index++) {
  const args = [...common, '--output', files[index], ...(index ? ['--continue', files[0]] : [])]
  const stdout = execFileSync(process.execPath, args, { cwd: root, env, timeout: 300000, encoding: 'utf8', maxBuffer: 1024 * 1024 })
  await writeFile(join(output, `process-${index + 1}.stdout.jsonl`), stdout)
  processEvidence.push({ ordinal: index + 1, exit_code: 0, command_arguments: args })
}
const first = JSON.parse(await readFile(files[0], 'utf8'))
const second = JSON.parse(await readFile(files[1], 'utf8'))
assert.equal(first.status, 'completed')
assert.equal(second.status, 'completed')
assert.equal(first.session_id, second.session_id)
assert.equal(first.turns.length, 1)
assert.equal(second.turns.length, 2)
assert.deepEqual(second.turns[1].tool_calls.map(call => call.name), ['acycle_inspect'])
const imported = first.turns[0].tool_results.flatMap(result => result.message?.content ?? [])
  .filter(block => block.type === 'text').map(block => { try { return JSON.parse(block.text) } catch { return null } })
  .find(value => value?.status === 'imported')
assert.ok(imported?.input_path)
assert.equal(JSON.parse(second.turns[1].tool_calls[0].arguments).input_path, imported.input_path)
assert.ok(second.turns[1].tool_results.length)
assert.ok(second.turns[1].tool_results.every(result => !result.message?.isError))
const userIds = []
for (const turn of second.turns) {
  const saved = JSON.parse(await readFile(turn.events_file, 'utf8'))
  assert.equal(saved.sessionId, first.session_id)
  const users = saved.events.filter(event => event.type === 'user/message' && event.data.source?.kind === 'user')
  assert.equal(users.length, 1)
  userIds.push(users[0].data.id)
}
assert.equal(new Set(userIds).size, 2)
const receipt = { schema_version: 1, status: 'passed', mode: 'keyless-scripted-infrastructure',
  scope: 'Two separate runner processes using the actual published SDK and persisted official Session. No live API or scientific computation.',
  session_id: first.session_id, distinct_user_message_ids: userIds, prior_import_path_retained: true,
  second_turn_inspects_the_genuine_prior_import: true, first_process_exited_before_second_started: true,
  catalog_inheritance: second.runtime.catalog_evidence, processes: processEvidence,
  receipts: files, scientific_execution_count: 0, live_model_requests: 0 }
await writeFile(join(output, 'resume-check.json'), JSON.stringify(receipt, null, 2) + '\n')
process.stdout.write(JSON.stringify({ status: receipt.status, session_id: receipt.session_id, output: join(output, 'resume-check.json') }) + '\n')
