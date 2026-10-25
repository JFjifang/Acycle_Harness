import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, writeFile, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { runBridge, loadSkills, apply } from '../index.mjs'

async function fixture(body) {
  const root = await mkdtemp(join(tmpdir(), 'acycle-plugin-'))
  const executable = join(root, 'python-fixture')
  await writeFile(executable, '#!/usr/bin/env python3\n' + body, { mode: 0o700 })
  return { root, executable }
}

test('bridge transports JSON literally without shell expansion', async () => {
  const { executable } = await fixture("import sys; sys.stdout.write(sys.stdin.read())")
  const request = { action: 'call', arguments: { path: 'a b/$(touch NEVER)/quote\'file.csv' } }
  assert.deepEqual(await runBridge(request, { python: executable }), request)
})

test('bridge observes cancellation and waits for subprocess exit', async () => {
  const { executable } = await fixture('import time; time.sleep(30)')
  const controller = new AbortController()
  const pending = runBridge({}, { python: executable, signal: controller.signal })
  setTimeout(() => controller.abort(), 100)
  await assert.rejects(pending, /cancelled/)
})

test('bridge reports errors and rejects non-JSON output', async () => {
  const { executable } = await fixture("print('MATLAB output must not pollute protocol')")
  await assert.rejects(runBridge({}, { python: executable }), /invalid JSON/)
})

test('packaged skill metadata strips frontmatter and resolves resources', async () => {
  const { root } = await fixture('')
  await mkdir(join(root, 'acycle-mini-robot'))
  await writeFile(join(root, 'acycle-mini-robot', 'SKILL.md'), '---\nname: acycle-mini-robot\ndescription: Run MATLAB\n---\nUse MATLAB original functions.\n')
  const [skill] = await loadSkills(root)
  assert.equal(skill.name, 'acycle-mini-robot')
  assert.equal(skill.content, 'Use MATLAB original functions.\n')
  assert.equal(skill.resourceBase.kind, 'directory')
})

test('optional SystemPrompt service does not block legacy plugin registration', async () => {
  const { executable, root } = await fixture("print('[]')")
  const registered = []
  const ctx = { get: () => undefined, tools: { register: tool => registered.push(tool.name) },
    skills: { registerProvider: () => {} } }
  await apply(ctx, { workspace: root, python: executable })
  assert.deepEqual(registered, ['acycle_import_attachment'])
})
