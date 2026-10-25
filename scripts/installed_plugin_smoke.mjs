/** Check the packaged plugin against the published official Cordis/tool/skill registries. */
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import { resolve, join } from 'node:path'
import { readFile } from 'node:fs/promises'
const runtimeRoot = resolve(process.argv[2] || '/workspace/harness-runtime-smoke')
const workspace = resolve(process.argv[3] || '.')
const pluginPath = resolve(process.argv[4] || join(workspace, 'plugin/index.mjs'))
const require = createRequire(join(runtimeRoot, 'package.json'))
const load = async name => import(pathToFileURL(require.resolve(name)).href)
const { Context, Service } = await load('@deepseek-ai/cordis')
const { default: ToolRuntime } = await load('@deepseek-ai/dsh-tools')
const { default: SystemPrompt } = await load('@deepseek-ai/dsh-system-prompt')
const { default: SkillRegistry } = await load('@deepseek-ai/dsh-skill')
const plugin = await import(pathToFileURL(pluginPath).href)
class WorkingDirectoryFixture extends Service {
  constructor(ctx) { super(ctx, 'workingDirectory') }
  async ensure() { return workspace }
}
const ctx = new Context()
try {
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime, { mode: 'native' })
  await ctx.plugin(SkillRegistry)
  await ctx.plugin(WorkingDirectoryFixture)
  const fiber = await ctx.plugin(plugin, { workspace })
  const tools = ctx.tools.schemas()
  assert.equal(tools.length, 9)
  const skills = await ctx.skills.list()
  assert.equal(skills.length, 8)
  for (const skill of skills) assert.ok((await ctx.skills.get(skill.name)).content.length > 100)
  const outcome = await ctx.tools.execute({ callId: 'acycle-smoke-1', name: 'acycle_capabilities',
    arguments: {}, signal: new AbortController().signal })
  assert.equal(outcome.isError, false, JSON.stringify(outcome))
  assert.equal(outcome.value.python_numerical_fallback, false)
  const version = JSON.parse(await readFile(require.resolve('@deepseek-ai/dsh-tools/package.json'), 'utf8')).version
  await fiber.dispose()
  assert.equal(ctx.tools.schemas().length, 0)
  assert.equal((await ctx.skills.list()).length, 0)
  console.log(JSON.stringify({ status: 'passed', dsh_tools_version: version, plugin_path: pluginPath,
    registered_tools: tools.map(x => x.name), registered_skills: skills.map(x => x.name),
    capabilities: outcome.value, disposal: 'passed',
    scope: 'Official Cordis, tools and skills registries with fixed workspace fixture; not a full GUI session.' }, null, 2))
} finally { await ctx.fiber.dispose() }
