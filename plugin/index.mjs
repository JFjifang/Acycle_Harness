/** Native Cordis plugin. All tools share the Python transport -> MATLAB dispatcher. */
import { spawn } from 'node:child_process'
import { readFile, readdir } from 'node:fs/promises'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'acycle-matlab'
export const inject = ['tools', 'skills', 'workingDirectory']
const skillRoot = fileURLToPath(new URL('./skills/', import.meta.url))
const MAX_OUTPUT = 16 * 1024 * 1024

/** No shell expansion; arguments and paths travel as JSON through stdin. */
export function runBridge(request, { python = process.env.ACYCLE_PYTHON || 'python3', signal,
                                     timeoutMs = 3_600_000 } = {}) {
  return new Promise((fulfill, reject) => {
    if (signal?.aborted) return reject(new Error('Acycle call cancelled'))
    const child = spawn(python, ['-m', 'acycle_deepseek.harness_bridge'], {
      stdio: ['pipe', 'pipe', 'pipe'], shell: false, detached: process.platform !== 'win32',
    })
    let stdout = '', stderr = '', failure, forceTimer
    const stop = (reason) => {
      if (failure) return
      failure = reason
      const kill = (kind) => {
        try {
          if (process.platform !== 'win32' && child.pid) process.kill(-child.pid, kind)
          else child.kill(kind)
        } catch { /* It may already have exited. */ }
      }
      kill('SIGTERM')
      forceTimer = setTimeout(() => kill('SIGKILL'), 5000)
      forceTimer.unref()
    }
    const abort = () => stop(new Error('Acycle call cancelled'))
    const timeout = setTimeout(() => stop(new Error('Acycle bridge timed out')), timeoutMs)
    timeout.unref()
    signal?.addEventListener('abort', abort, { once: true })
    const clean = () => {
      clearTimeout(timeout); clearTimeout(forceTimer)
      signal?.removeEventListener('abort', abort)
    }
    child.stdout.on('data', data => {
      stdout += data.toString()
      if (stdout.length > MAX_OUTPUT) stop(new Error('Acycle bridge output limit exceeded'))
    })
    child.stderr.on('data', data => { if (stderr.length < 20000) stderr += data.toString() })
    child.on('error', error => { clean(); reject(error) })
    child.on('close', code => {
      clean()
      if (failure) return reject(failure)
      if (code !== 0) {
        const secret = process.env.DEEPSEEK_API_KEY
        const detail = secret ? stderr.replaceAll(secret, '[REDACTED]') : stderr
        return reject(new Error(`Acycle bridge exited ${code}: ${detail.slice(-4000)}`))
      }
      try { fulfill(JSON.parse(stdout)) }
      catch { reject(new Error('Acycle bridge returned invalid JSON')) }
    })
    child.stdin.on('error', () => {})
    child.stdin.end(JSON.stringify(request))
  })
}

export async function loadSkills(root = skillRoot) {
  let entries
  try { entries = await readdir(root, { withFileTypes: true }) }
  catch (error) { if (error.code === 'ENOENT') return []; throw error }
  const skills = []
  for (const entry of entries.filter(e => e.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
    const path = join(root, entry.name, 'SKILL.md')
    const content = await readFile(path, 'utf8')
    const nameMatch = content.match(/^name:\s*["']?([a-z0-9-]+)["']?\s*$/m)
    const descriptionMatch = content.match(/^description:\s*(.+)$/m)
    if (!nameMatch || !descriptionMatch) throw new Error(`Missing skill metadata: ${path}`)
    const description = descriptionMatch[1].replace(/^['"]|['"]$/g, '')
    skills.push({ name: nameMatch[1], description, path, source: 'bundled', provider: name,
      invocation: { modelInvocable: true, userInvocable: true },
      resourceBase: { kind: 'directory', path: join(root, entry.name) },
      content: content.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '') })
  }
  return skills
}

export async function apply(ctx, config = {}) {
  const python = config.python || process.env.ACYCLE_PYTHON || 'python3'
  const configuredWorkspace = config.workspace || process.env.ACYCLE_WORKSPACE
  const options = { python, timeoutMs: config.timeoutMs || 3_600_000 }
  const schemas = await runBridge({ action: 'schemas' }, options)
  for (const schema of schemas) {
    const fn = schema.function
    ctx.tools.register({
      name: fn.name, description: fn.description, parameters: fn.parameters,
      output: { schema: { type: 'object', additionalProperties: true },
                render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
      async execute(args, exec) {
        const workspace = configuredWorkspace || (exec.agent
          ? await ctx.workingDirectory.ensure(exec.agent, exec.signal) : process.cwd())
        return runBridge({ action: 'call', name: fn.name, arguments: args,
                           workspace: resolve(workspace) }, { ...options, signal: exec.signal })
      },
    })
  }
  const skills = await loadSkills()
  const byName = new Map(skills.map(skill => [skill.name, skill]))
  ctx.skills.registerProvider(() => ({
    name,
    list: async () => skills.map(({ content, ...skill }) => ({ ...skill, rank: 600, locator: skill.name })),
    get: async candidate => byName.get(candidate.name),
  }))
}
