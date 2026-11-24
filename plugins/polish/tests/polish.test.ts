import { expect, test } from 'claude-code/testing'
import type { ModelCompleteResult, On, UiCopyResult } from 'claude-code'
import type { Engine } from 'claude-code/testing'

const RULES = '# Polish rules\n\nSynthetic rule: fix the grammar.\n'
const usage = (output_tokens = 12) => ({
  input_tokens: 40,
  output_tokens,
  cache_read_input_tokens: 0,
  cache_creation_input_tokens: 0,
})

type Setup = {
  boxes?: string[]
  rules?: string | null
  reply?: ModelCompleteResult
  refuse?: boolean
  isFilled?: boolean
  copy?: UiCopyResult
}

// Stands for the engine beneath the mod and records what the mod asked of it.
async function harness($: Engine, on: On, setup: Setup = {}) {
  const boxes = [...(setup.boxes ?? [''])]
  const seen = {
    registered: [] as unknown[],
    reads: [] as string[],
    requests: [] as { model: string; system?: string; prompt: string; effort?: string }[],
    fills: [] as { text: string; mode?: string }[],
    copies: [] as string[],
    toasts: [] as string[],
    statuses: [] as (string | undefined)[],
  }
  on('command.register', (_, e) => {
    seen.registered.push(e)
    return { value: { command: 'polish' } }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('prompt.read', () => {
    const text = boxes.length > 1 ? boxes.shift()! : boxes[0]!
    return { value: { text, cursor: text.length } }
  })
  on('fs.read', (_, e) => {
    seen.reads.push(e.path)
    if (setup.rules === null) throw new Error('ENOENT')
    return { value: setup.rules ?? RULES }
  })
  on('model.complete', (_, e) => {
    seen.requests.push({ model: e.model, system: e.system, prompt: e.prompt, effort: e.effort })
    // A throw leaves the call unanswered, so it rejects as a refused send does.
    if (setup.refuse) throw new Error('model blocked')
    return { value: setup.reply ?? { isAnswered: true, text: ' Polished text. \n', usage: usage() } }
  })
  on('prompt.fill', (_, e) => {
    seen.fills.push({ text: e.text, mode: e.mode })
    return setup.isFilled === false
      ? { isFilled: false, refusal: 'dialog', text: '', cursor: 0 }
      : { isFilled: true, text: e.text, cursor: e.text.length }
  })
  on('ui.copy', (_, e) => {
    seen.copies.push(e.text)
    return { value: setup.copy ?? { isCopied: true } }
  })
  on('ui.toast', (_, e) => {
    seen.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', (_, e) => {
    seen.statuses.push(e.text)
    return { value: undefined }
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  // As the person's Enter on `/<command> <args>` reaches the engine.
  const run = (args = '', command = 'polish') =>
    $.command.run({
      command,
      args,
      origin: { kind: 'composer' },
      presentation: { isFullscreen: false, columns: 80 },
    })
  return { seen, run }
}

test('the mod registers /polish and /polish-copy to run even mid-turn', async ($, on) => {
  const { seen } = await harness($, on)
  expect(seen.registered).toEqual([
    {
      name: 'polish',
      description: 'Polish text into the prompt box without sending it',
      argumentHint: '[text]',
      immediate: true,
    },
    {
      name: 'polish-copy',
      description: 'Polish text and copy it to the clipboard',
      argumentHint: '[text]',
      immediate: true,
    },
  ])
})

test('the draft in the box is polished in place, with nothing for the transcript', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['um so plz fix teh loader'] })
  const result = await run()
  expect(result.text).toBeUndefined()
  expect(seen.reads).toEqual([expect.stringMatching(/\/skills\/polish-text\/rules\.md$/)])
  expect(seen.requests).toHaveLength(1)
  const [request] = seen.requests
  expect(request!.model).toBe('haiku')
  expect(request!.effort).toBe('low')
  expect(request!.prompt).toBe('um so plz fix teh loader')
  expect(request!.system!.startsWith(RULES.trim())).toBe(true)
  expect(request!.system).toMatch(/Return only the polished text\./)
  expect(seen.fills).toEqual([{ text: 'Polished text.', mode: 'replace' }])
  expect(seen.toasts).toEqual([])
  expect(seen.statuses).toEqual(['Polishing...', undefined])
})

test('/polish <text> polishes the arguments into the empty box', async ($, on) => {
  const { seen, run } = await harness($, on)
  await run('hey can u check teh deploy')
  expect(seen.requests[0]!.prompt).toBe('hey can u check teh deploy')
  expect(seen.fills).toEqual([{ text: 'Polished text.', mode: 'replace' }])
})

test('nothing to polish makes no request', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['   '] })
  expect((await run()).text).toBeUndefined()
  expect(seen.requests).toEqual([])
  expect(seen.toasts).toEqual([expect.stringMatching(/^Nothing to polish\./)])
})

test('unreadable rules make no request', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['raw draft'], rules: null })
  await run()
  expect(seen.requests).toEqual([])
  expect(seen.fills).toEqual([])
  expect(seen.toasts).toEqual([expect.stringMatching(/Cannot read the polish rules/)])
})

for (const [name, reply, reason] of [
  [
    'an API error',
    { isAnswered: false, reason: 'api-error', status: 529, error: 'overloaded', usage: usage(0) },
    /the API answered overloaded/,
  ],
  ['a timeout', { isAnswered: false, reason: 'aborted', usage: usage(0) }, /timed out/],
  ['an empty reply', { isAnswered: true, text: '  ', usage: usage(1) }, /no text/],
  ['a cut-off reply', { isAnswered: true, text: 'Half a', usage: usage(8192) }, /cut off/],
] as const) {
  test(`${name} leaves the draft alone and says why`, async ($, on) => {
    const { seen, run } = await harness($, on, { boxes: ['raw draft'], reply })
    expect((await run()).text).toBeUndefined()
    expect(seen.fills).toEqual([])
    expect(seen.toasts).toEqual([expect.stringMatching(reason)])
    expect(seen.toasts[0]).toMatch(/The draft is unchanged\.$/)
    expect(seen.statuses).toEqual(['Polishing...', undefined])
  })
}

test('a request the engine refuses leaves the draft alone and says why', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['raw draft'], refuse: true })
  expect((await run()).text).toBeUndefined()
  expect(seen.fills).toEqual([])
  expect(seen.toasts).toEqual([expect.stringMatching(/^Polish failed: Claude Code refused the request/)])
  expect(seen.toasts[0]).toMatch(/The draft is unchanged\.$/)
  expect(seen.statuses).toEqual(['Polishing...', undefined])
})

test('typing during the request is kept and the result shown instead', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['raw draft', 'raw draft and more'] })
  const result = await run()
  expect(seen.fills).toEqual([])
  expect(result.text).toMatch(/^The draft changed while polishing/)
  expect(result.text).toMatch(/Polished text\.$/)
})

test('a box that cannot take the result shows it as output', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['raw draft'], isFilled: false })
  const result = await run()
  expect(seen.fills).toHaveLength(1)
  expect(result.text).toBe('Polished text.')
})

test('/polish-copy <text> copies the result and leaves the box alone', async ($, on) => {
  const { seen, run } = await harness($, on)
  const result = await run('hey can u check teh deploy', 'polish-copy')
  expect(result.text).toBeUndefined()
  expect(seen.requests).toHaveLength(1)
  expect(seen.requests[0]!.prompt).toBe('hey can u check teh deploy')
  expect(seen.requests[0]!.model).toBe('haiku')
  expect(seen.copies).toEqual(['Polished text.'])
  expect(seen.fills).toEqual([])
  expect(seen.toasts).toEqual(['Polished text copied.'])
  expect(seen.statuses).toEqual(['Polishing...', undefined])
})

test('/polish-copy from a key copies the draft in the box', async ($, on) => {
  const { seen, run } = await harness($, on, { boxes: ['um so plz fix teh loader'] })
  await run('', 'polish-copy')
  expect(seen.requests[0]!.prompt).toBe('um so plz fix teh loader')
  expect(seen.copies).toEqual(['Polished text.'])
  expect(seen.fills).toEqual([])
})

test('/polish-copy with nothing to polish makes no request', async ($, on) => {
  const { seen, run } = await harness($, on)
  expect((await run('', 'polish-copy')).text).toBeUndefined()
  expect(seen.requests).toEqual([])
  expect(seen.copies).toEqual([])
  expect(seen.toasts).toEqual(['Nothing to polish. Run /polish-copy <text>.'])
})

test('/polish-copy copies nothing when the polish fails', async ($, on) => {
  const reply = { isAnswered: false, reason: 'aborted', usage: usage(0) } as const
  const { seen, run } = await harness($, on, { reply })
  expect((await run('raw draft', 'polish-copy')).text).toBeUndefined()
  expect(seen.copies).toEqual([])
  expect(seen.toasts).toEqual([expect.stringMatching(/^Polish failed: it timed out\./)])
})

test('a clipboard that cannot take it shows the result as output', async ($, on) => {
  const copy = { isCopied: false, reason: 'no-clipboard' } as const
  const { seen, run } = await harness($, on, { copy })
  const result = await run('raw draft', 'polish-copy')
  expect(seen.copies).toEqual(['Polished text.'])
  expect(seen.toasts).toEqual([])
  expect(result.text).toMatch(/^Could not copy it \(no-clipboard\)\./)
  expect(result.text).toMatch(/Polished text\.$/)
})
