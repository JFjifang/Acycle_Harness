/** Keyless infrastructure fixture. This adapter is NEVER a real-model acceptance test. */
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

export const name = 'acycle-conversation-fixture'
export const inject = ['llm']

export async function apply(ctx, config) {
  const require = createRequire(join(config.runtimeRoot, 'package.json'))
  const { LlmAdapter } = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-llm')).href)
  class FixtureAdapter extends LlmAdapter {
    step = 0
    async * stream(options) {
      const step = this.step++
      const names = ['skill', 'acycle_capabilities', 'acycle_import_attachment', null, 'acycle_inspect']
      const name = names[step] ?? null
      let args = step === 0 ? { name: 'acycle-intake' } : {}
      if (step === 4) {
        const userMessages = options.messages.filter(message => message.role === 'user')
        if (userMessages.length < 2) throw new Error('The official runtime did not retain both independent user messages')
        const imported = options.messages.flatMap(message => message.role === 'tool' ? message.content ?? [] : [])
          .filter(block => block.type === 'text')
          .map(block => { try { return JSON.parse(block.text) } catch { return null } })
          .find(value => value?.status === 'imported')
        if (!imported?.input_path) throw new Error('The second user turn lost the genuine prior attachment tool result')
        args = { input_path: imported.input_path }
      }
      if (name) {
        const id = `fixture-call-${step}`
        const argumentsText = JSON.stringify(args)
        yield { type: 'block-start', index: 0, blockType: 'tool-call', id, name }
        yield { type: 'tool-call-delta', index: 0, id, name, argumentsDelta: argumentsText }
        yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name, arguments: argumentsText } }
        yield { type: 'finish', reason: { kind: 'tool-calls' } }
      } else {
        const text = 'Keyless infrastructure fixture completed; no scientific or real-model claim.'
        yield { type: 'block-start', index: 0, blockType: 'text' }
        yield { type: 'text-delta', index: 0, text }
        yield { type: 'block-end', index: 0, block: { type: 'text', text } }
        yield { type: 'finish', reason: { kind: 'stop' } }
      }
    }
  }
  ctx.llm.registerAdapter(['acycle-fixture'], new FixtureAdapter())
}
