import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, writeFile, mkdir, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runBridge, loadSkills, apply, inject } from '../index.mjs'

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

test('Desktop MATLAB paths are confined to the bridge child environment', async t => {
  const { root, executable } = await fixture("import os,json; print(json.dumps({key:os.environ.get(key) for key in ['ACYCLE_ROOT','MATLAB_EXECUTABLE','ACYCLE_BACKEND']}))")
  t.after(() => rm(root, { recursive: true, force: true }))
  const before = { root: process.env.ACYCLE_ROOT, matlab: process.env.MATLAB_EXECUTABLE, backend: process.env.ACYCLE_BACKEND }
  const environment = { ACYCLE_ROOT: '/local/Acycle source', MATLAB_EXECUTABLE: '/Applications/MATLAB/bin/matlab', ACYCLE_BACKEND: 'local' }
  assert.deepEqual(await runBridge({}, { python: executable, environment }), environment)
  assert.deepEqual({ root: process.env.ACYCLE_ROOT, matlab: process.env.MATLAB_EXECUTABLE, backend: process.env.ACYCLE_BACKEND }, before)
})

test('bridge observes cancellation and waits for subprocess exit', async () => {
  const { executable } = await fixture('import time; time.sleep(30)')
  const controller = new AbortController()
  const pending = runBridge({}, { python: executable, signal: controller.signal })
  setTimeout(() => controller.abort(), 100)
  await assert.rejects(pending, /cancelled/)
})

test('native cancellation lets Python stop a TERM-ignoring MATLAB process group and save evidence',
  { skip: process.platform === 'win32' ? 'POSIX process-group supervision fixture' : false }, async t => {
    const { root, executable } = await fixture('')
    t.after(() => rm(root, { recursive: true, force: true }))
    const marker = join(root, 'started')
    const pidFile = join(root, 'child.pid')
    const child = join(root, 'fake-matlab.py')
    const output = join(root, 'outputs')
    await writeFile(child, `import os,signal,time\nfrom pathlib import Path\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath(${JSON.stringify(marker)}).write_text('started')\nPath(${JSON.stringify(pidFile)}).write_text(str(os.getpid()))\nwhile True: time.sleep(0.05)\n`)
    const source = fileURLToPath(new URL('../../src', import.meta.url))
    await writeFile(executable, `#!/usr/bin/env python3\nimport sys\nsys.path.insert(0,${JSON.stringify(source)})\nfrom acycle_deepseek.matlab_runner import run_matlab\nrun_matlab([sys.executable,${JSON.stringify(child)}],${JSON.stringify(output)},startup_marker=${JSON.stringify(marker)},startup_timeout=10,timeout=60)\n`, { mode: 0o700 })
    const controller = new AbortController()
    const rejected = assert.rejects(runBridge({}, { python: executable, signal: controller.signal }), /cancelled/)
    let pid
    const deadline = Date.now() + 5000
    while (!pid && Date.now() < deadline) {
      try { pid = Number(await readFile(pidFile, 'utf8')) } catch (error) { if (error.code !== 'ENOENT') throw error }
      if (!pid) await new Promise(resolve => setTimeout(resolve, 25))
    }
    assert.ok(pid, 'fake MATLAB reached its marker with SIGTERM ignored')
    controller.abort()
    await rejected
    const receipt = JSON.parse(await readFile(join(output, 'matlab-launch.json'), 'utf8'))
    assert.equal(receipt.status, 'interrupted')
    assert.equal(receipt.returncode, -9, 'Python escalated the separate MATLAB group after its own grace')
    assert.equal(receipt.attempts, 1)
    assert.equal(receipt.automatic_retry, false)
    assert.ok(receipt.elapsed_seconds >= 5)
    assert.throws(() => process.kill(pid, 0), error => error.code === 'ESRCH', 'the fake MATLAB child was reaped')
    t.diagnostic(JSON.stringify({ fixture: 'TERM-ignoring process; no MATLAB science', status: receipt.status,
      returncode: receipt.returncode, attempts: receipt.attempts, automatic_retry: receipt.automatic_retry,
      elapsed_seconds: receipt.elapsed_seconds, child_reaped: true }))
  })

test('bridge reports errors and rejects non-JSON output', async () => {
  const { executable } = await fixture("print('MATLAB output must not pollute protocol')")
  await assert.rejects(runBridge({}, { python: executable }), /invalid JSON/)
})

test('bridge retains structured failed-run diagnostics while rejecting the tool call', async () => {
  const { executable } = await fixture("import json,sys; print(json.dumps({'status':'failed','run_id':'20261025T000000Z-123456abcdef','operation':'tune','matlab_error':'Tie points are not monotonic','diagnostics':{'stderr':'saved/stderr.log'}})); sys.exit(1)")
  await assert.rejects(runBridge({}, { python: executable }), error => {
    assert.match(error.message, /20261025T000000Z-123456abcdef/)
    assert.match(error.message, /Tie points are not monotonic/)
    assert.match(error.message, /saved\/stderr.log/)
    return true
  })
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

test('current Harness requires workflow policy and registers it before tools', async () => {
  const { executable, root } = await fixture("print('[]')")
  const registered = []
  const ctx = { systemPrompt: { section: section => registered.push(section.name) },
    tools: { register: tool => registered.push(tool.name) },
    skills: { registerProvider: () => {} } }
  assert.ok(inject.includes('systemPrompt'))
  await apply(ctx, { workspace: root, python: executable })
  assert.deepEqual(registered, ['acycle:research-workflow', 'acycle_import_attachment'])
})
