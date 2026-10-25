import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, mkdir, writeFile, readFile, symlink, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { attachOutputs, deliveryConfig, modelValue, renderResult } from '../attachments.mjs'

const runId = '20261025T000000Z-123456abcdef'
const exec = () => ({ signal: new AbortController().signal })

test('compact model result preserves statistics, warnings and source mismatches', () => {
  const provenance = { reference_commit: 'abc', all_used_sources_match_reference: false,
    files: [{ relative_path: 'ok.m', sha256: 'a', matches_reference: true },
      { relative_path: 'changed.m', sha256: 'b', matches_reference: false }] }
  const value = { status: 'complete', summary: { monte_carlo_count: 19, statistical_limitations: ['exploratory only'] },
    provenance, result: { status: 'complete', summary: { monte_carlo_count: 19 }, provenance,
      warnings: ['not a publication significance test'], error: { diagnostic: 'retained' } } }
  const rendered = modelValue(value)
  assert.equal(rendered.provenance.files, undefined)
  assert.equal(rendered.provenance.source_file_count, 2)
  assert.deepEqual(rendered.provenance.source_mismatches, [provenance.files[1]])
  assert.deepEqual(rendered.summary, value.summary)
  assert.deepEqual(rendered.matlab_result.warnings, value.result.warnings)
  assert.deepEqual(rendered.matlab_result.error, value.result.error)
  assert.equal(value.provenance.files.length, 2, 'canonical result remains intact')
})

test('missing attachment services preserve science and path delivery', async () => {
  const value = { status: 'complete', run_id: runId, artifacts: { spectrum: '/science/spectrum.png' } }
  const outcome = await attachOutputs({ get: () => undefined }, value, '/unused', exec(), deliveryConfig())
  assert.equal(outcome.status, 'complete')
  assert.equal(outcome.presentation.status, 'paths_only')
  assert.deepEqual(outcome.artifacts, value.artifacts)
  assert.equal(renderResult({}, outcome).length, 1)
})

test('failed presentation cannot turn a completed MATLAB result into a failed analysis', async t => {
  const workspace = await mkdtemp(join(tmpdir(), 'acycle-delivery-failure-'))
  t.after(() => rm(workspace, { recursive: true, force: true }))
  const outputs = join(workspace, '.acycle', 'runs', runId, 'outputs')
  await mkdir(outputs, { recursive: true })
  const csv = join(outputs, 'spectrum.csv')
  await writeFile(csv, 'frequency,power\n1,2\n')
  const attachments = { saveFile: async ({ data, name }) => ({ name, bytes: data.length, attachmentId: 'fixture' }) }
  const ctx = { get: () => attachments, tools: { get: () => ({}), execute: async () => { throw new Error('display transport unavailable') } } }
  const outcome = await attachOutputs(ctx, { status: 'complete', run_id: runId, artifacts: { spectrum: csv } }, workspace,
    { ...exec(), agent: {} }, deliveryConfig())
  assert.equal(outcome.status, 'complete')
  assert.equal(outcome.presentation.status, 'partial')
  assert.equal(outcome.presentation.delivery.status, 'failed')
  assert.match(outcome.presentation.warnings.join(' '), /instead of recomputing/)
  assert.equal(await readFile(csv, 'utf8'), 'frequency,power\n1,2\n')
})

test('artifact delivery excludes a symlink escaping recorded outputs and oversized files', async t => {
  const workspace = await mkdtemp(join(tmpdir(), 'acycle-delivery-boundary-'))
  t.after(() => rm(workspace, { recursive: true, force: true }))
  const outputs = join(workspace, '.acycle', 'runs', runId, 'outputs')
  await mkdir(outputs, { recursive: true })
  const outside = join(workspace, 'private.csv')
  await writeFile(outside, 'private')
  await symlink(outside, join(outputs, 'escape.csv'))
  await writeFile(join(outputs, 'large.csv'), '12345')
  let saved = 0
  const ctx = { get: () => ({ saveFile: async () => { saved++; throw new Error('should not copy') } }) }
  const value = { status: 'complete', run_id: runId, artifacts: { escape: join(outputs, 'escape.csv'), large: join(outputs, 'large.csv') } }
  const outcome = await attachOutputs(ctx, value, workspace, exec(), deliveryConfig({ maxArtifactBytes: 4 }))
  assert.equal(saved, 0)
  assert.equal(outcome.status, 'complete')
  assert.equal(outcome.presentation.status, 'partial')
  assert.equal(outcome.presentation.skipped.length, 2)
  assert.deepEqual(outcome.artifacts, value.artifacts)
})
