import type { EngineInterface, ModelCompleteResult, Register } from 'claude-code'

// Polish a draft in one side request. /polish puts the result in the prompt
// box, unsent. /polish-copy puts it on the clipboard. The rules are the
// polish-text skill's shared rules.md.
const RULES = 'skills/polish-text/rules.md'
const OUTPUT =
  'Return only the polished text. The text to polish follows in the user message.'
const MODEL = 'haiku'
const MAX_TOKENS = 8192

// The polished text, or undefined after a toast that says why not.
// Notices are toasts: nothing goes to the transcript or the model.
async function polish(
  $: EngineInterface,
  draft: string,
  lock: { running: boolean },
): Promise<string | undefined> {
  if (lock.running) {
    $.ui.toast('Polish is already running.')
    return
  }
  let rules: string
  try {
    rules = await $.fs.read(`${$.plugin.root}/${RULES}`)
  } catch {
    $.ui.toast(`Cannot read the polish rules at ${RULES} in the polish plugin.`)
    return
  }

  lock.running = true
  $.ui.status('Polishing...')
  try {
    let reply: ModelCompleteResult
    try {
      reply = await $.model.complete({
        model: MODEL,
        system: `${rules.trim()}\n\n${OUTPUT}`,
        prompt: draft,
        effort: 'low',
        maxTokens: MAX_TOKENS,
        timeoutMs: 60_000,
      })
    } catch (err) {
      // Rejects only when the engine refuses to send, such as a blocked model.
      const why = err instanceof Error ? err.message : String(err)
      $.ui.toast(`Polish failed: Claude Code refused the request (${why}). The draft is unchanged.`)
      return
    }
    const polished = reply.isAnswered ? reply.text.trim() : ''
    const failure = !reply.isAnswered
      ? reply.reason === 'api-error'
        ? `the API answered ${reply.error}`
        : reply.reason === 'aborted'
          ? 'it timed out'
          : 'the model returned no text'
      : reply.usage.output_tokens >= MAX_TOKENS
        ? 'the reply was cut off'
        : !polished
          ? 'the model returned no text'
          : undefined
    if (failure) {
      $.ui.toast(`Polish failed: ${failure}. The draft is unchanged.`)
      return
    }
    return polished
  } finally {
    lock.running = false
    $.ui.status(undefined)
  }
}

export const register: Register = on => {
  const lock = { running: false }

  on('session.start', async ($, e, next) => {
    // Literal names: validate then reads both hooks as answering their own command.
    await $.command.register({
      name: 'polish',
      description: 'Polish text into the prompt box without sending it',
      argumentHint: '[text]',
      immediate: true,
    })
    await $.command.register({
      name: 'polish-copy',
      description: 'Polish text and copy it to the clipboard',
      argumentHint: '[text]',
      immediate: true,
    })

    return next(e)
  })

  on('command.run', { command: 'polish' }, async ($, e) => {
    const before = (await $.prompt.read()).text
    const draft = (e.args.trim() ? e.args : before).trim()
    if (!draft) {
      $.ui.toast(
        'Nothing to polish. Run /polish <text>. To polish the draft in the box, bind a key to command:polish.',
      )
      return {}
    }
    const polished = await polish($, draft, lock)
    if (polished === undefined) return {}

    // Typing went on while the request ran: keep it, show the result instead.
    if ((await $.prompt.read()).text !== before)
      return { text: `The draft changed while polishing, so it was left alone.\n\n${polished}` }
    const filled = await $.prompt.fill({ text: polished, mode: 'replace' })
    if (!filled.isFilled) return { text: polished }

    return {}
  })

  // Leaves the box alone. Without arguments it takes the box's draft, which
  // only a key binding can hand it: typing the command replaces the draft.
  on('command.run', { command: 'polish-copy' }, async ($, e) => {
    const draft = (e.args.trim() ? e.args : (await $.prompt.read()).text).trim()
    if (!draft) {
      $.ui.toast('Nothing to polish. Run /polish-copy <text>.')
      return {}
    }
    const polished = await polish($, draft, lock)
    if (polished === undefined) return {}

    const copied = await $.ui.copy({ text: polished })
    if (!copied.isCopied)
      return { text: `Could not copy it (${copied.reason}). The polished text:\n\n${polished}` }
    $.ui.toast('Polished text copied.')
    return {}
  })
}
