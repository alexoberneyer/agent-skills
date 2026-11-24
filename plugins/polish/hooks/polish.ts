import type { ModelCompleteResult, Register } from 'claude-code'

// Polish a draft in one side request and put the result in the prompt box,
// unsent. The rules are the polish-text skill's shared rules.md.
const RULES = 'skills/polish-text/rules.md'
const OUTPUT =
  'Return only the polished text. The text to polish follows in the user message.'
const MODEL = 'haiku'
const MAX_TOKENS = 8192

export const register: Register = on => {
  let running = false

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'polish',
      description: 'Polish text into the prompt box without sending it',
      argumentHint: '[text]',
      immediate: true,
    })

    return next(e)
  })

  on('command.run', { command: 'polish' }, async ($, e) => {
    // Nothing goes to the transcript or the model unless the box can't take
    // the result. Notices are toasts.
    const before = (await $.prompt.read()).text
    const draft = (e.args.trim() ? e.args : before).trim()
    if (!draft) {
      $.ui.toast(
        'Nothing to polish. Run /polish <text>. To polish the draft in the box, bind a key to command:polish.',
      )
      return {}
    }
    if (running) {
      $.ui.toast('Polish is already running.')
      return {}
    }
    let rules: string
    try {
      rules = await $.fs.read(`${$.plugin.root}/${RULES}`)
    } catch {
      $.ui.toast(`Cannot read the polish rules at ${RULES} in the polish plugin.`)
      return {}
    }

    running = true
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
        return {}
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
        return {}
      }

      // Typing went on while the request ran: keep it, show the result instead.
      if ((await $.prompt.read()).text !== before)
        return { text: `The draft changed while polishing, so it was left alone.\n\n${polished}` }
      const filled = await $.prompt.fill({ text: polished, mode: 'replace' })
      if (!filled.isFilled) return { text: polished }

      return {}
    } finally {
      running = false
      $.ui.status(undefined)
    }
  })
}
