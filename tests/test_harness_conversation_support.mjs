import assert from 'node:assert/strict'
import test from 'node:test'
import { scientificNames, scientificOutcome, turnExecutionPolicy } from '../scripts/harness_conversation_support.mjs'

const call = (name, callId) => ({ name, callId })
const result = (callId, value, isError = false) => ({ message: {
  toolCallId: callId, isError, content: [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value) }],
} })

test('new preparation and tuning operations count toward the science budget', () => {
  assert(scientificNames.has('acycle_interpolate_pro'))
  assert(scientificNames.has('acycle_tune'))
  assert(!scientificNames.has('acycle_get_run'))
  const outcome = scientificOutcome({
    tool_calls: [call('acycle_interpolate_pro', 'one'), call('acycle_tune', 'two')],
    tool_results: [result('one', { run_id: 'pro', status: 'completed', operation: 'interpolate_pro' }),
      result('two', { run_id: 'tune', status: 'completed', operation: 'tune', parent_run_id: 'old-tune' })],
  })
  assert.equal(outcome.scientific_calls, 2)
  assert.deepEqual(outcome.completed_runs.map(run => run.operation), ['interpolate_pro', 'tune'])
})

test('v0.5 structured RunError survives native error prefixes and isError omissions', () => {
  const failure = { status: 'failed', run_id: 'failed-run', operation: 'tune', error: 'Insufficient extrema',
    diagnostics: { stdout: 'matlab.log' } }
  const outcome = scientificOutcome({ tool_calls: [call('acycle_tune', 'one')],
    tool_results: [result('one', 'Error: Acycle bridge exited 1: ' + JSON.stringify(failure))] })
  assert.equal(outcome.completed_runs.length, 0)
  assert.deepEqual(outcome.failures[0].structured_failure, failure)
})

test('a successful early stage does not erase a later failed scientific stage', () => {
  const outcome = scientificOutcome({
    tool_calls: [call('acycle_analyze', 'one'), call('acycle_ecoco', 'two')],
    tool_results: [result('one', { status: 'completed', run_id: 'depth', operation: 'analyze' }),
      result('two', { status: 'failed', run_id: 'map', error: 'COCOUnresolved' }, true)],
  })
  assert.equal(outcome.completed_runs.length, 1)
  assert.equal(outcome.failures.length, 1)
})

test('read-only retrieval and success-shaped prose cannot satisfy a fresh scientific stage', () => {
  const outcome = scientificOutcome({
    tool_calls: [call('acycle_get_run', 'one'), call('acycle_analyze', 'two')],
    tool_results: [result('one', { status: 'completed', run_id: 'old' }), result('two', 'Completed successfully.')],
  })
  assert.equal(outcome.completed_runs.length, 0)
})

test('public scenario budgets override legacy defaults without becoming model instructions', () => {
  const turn = { execution_policy: { min_completed_scientific_runs: 6, max_scientific_calls: 8 },
    acceptance: { hidden: true } }
  assert.deepEqual(turnExecutionPolicy(turn), {
    kind: 'scientific', minimum_completed_runs: 6, maximum_scientific_calls: 8, maximum_tool_calls: 70,
  })
  assert.equal(turnExecutionPolicy(turn, { maxScientificCalls: '10' }).maximum_scientific_calls, 10)
  assert.throws(() => turnExecutionPolicy(turn, { maxScientificCalls: '2' }), /smaller/)
  assert.equal(turnExecutionPolicy({ execution_policy: { kind: 'read_only' } }).maximum_scientific_calls, 0)
})
