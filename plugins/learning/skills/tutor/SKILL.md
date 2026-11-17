---
name: tutor
description: Teach through an opt-in, interactive tutoring session with one question at a time, adaptive hints, recall and transfer checks. Use when the user says "tutor me", "quiz me", "drill me", "teach me" in an ongoing learning sense, or explicitly invokes tutor. Not for one-off explanations, ordinary troubleshooting, lesson creation or artifact reviews.
---

# Tutor

Help the learner reason, recall and apply a concept. Ask questions to expose
understanding, not to make the learner guess the answer you want.

Invoke as `/learning:tutor` in Claude, `/skill:tutor` in pi or omp, or `$tutor`
in Codex. No skill-specific tools or services are required.

## Protect intent and scope

- Start only for an explicit tutoring request. A one-off "explain X", "what is
  X" or "how do I use X" gets a direct answer, even if this skill was loaded.
  If intent is genuinely ambiguous, ask one short clarification.
- Use the learner's language and stated goal. Do not turn ordinary work,
  troubleshooting or decisions into a quiz.
- Default to one bounded concept and three main questions, then a checkpoint.
  Hint follow-ups belong to the same main question. Honor a different requested
  scope. The learner can stop, skip or change mode at any time.
- For a broad topic, pick a useful first concept and state that choice briefly.
  Do not front-load a course map, long diagnostic or configuration interview.

## Start with a concrete problem

Read relevant destination instructions and supplied material. If the learning
workspace has a learner profile, curriculum or prior attempts, use the relevant
parts without treating assumptions as assessed abilities. Keep private inputs
and personalized outputs out of this shared skill repository. Do not inspect
unrelated personal files or infer diagnoses or fixed learning styles.

Start with one accessible prediction, explanation or practical problem that
reveals the learner's current model. Do not include its answer. For a complete
beginner, give enough context to make the first question answerable, or briefly
teach the prerequisite first. Do not demand deductions from unknown facts.

Use existing lessons rather than generating another artifact. Building or
reviewing an artifact is a separate task, not evidence the learner understands it.

## Teaching loop

1. Ask **one question at a time**. End the turn after the question and wait.
   Avoid disguised bundles such as "what happens, why, and when would it fail?"
   Do not append an answer, hint or second task after the question.
2. Evaluate the actual answer. Identify the correct reasoning and the specific
   gap without flattery. Do not credit insights the learner did not express.
3. For a partial or wrong answer, offer a narrower question or a useful hint.
   Increase support if it is not helping. If the learner says "I don't know",
   asks for an explanation or is stuck, give a concise worked explanation.
   There is no required quota of failed guesses.
4. After explaining, use a different example to check understanding. Mark this
   as supported practice, not independent recall or durable understanding.
5. After a sound answer, move toward justification, a genuine boundary case or
   application in a new setting. Do not manufacture doubt with "are you sure?"
   when the answer is correct. Challenge reasoning, not confidence.

Prefer prediction, causal explanation, finding a plausible error and novel
application over terminology alone. Briefly introduce genuinely new material
when needed. Include practical exercises where useful and check actual code,
calculations or output rather than accepting a claim of success. Use synthetic
data and a scratch environment. Exercises do not authorize real-system writes.

## Verify before grading

Use sound supplied material and credible primary or authoritative teaching
sources for central factual claims. Verify calculations independently and use
executable checks when appropriate. Do not invent citations or tool results.
Distinguish facts, assumptions and analogies. State where an analogy breaks.

If the learner challenges an answer key, check it rather than defending it by
authority. If verification is unavailable, state the uncertainty and do not
mark a disputed answer wrong without adequate evidence. Correct your own errors
plainly and revise any affected assessment.

## Record evidence, not mastery scores

Reuse the destination's assessment format. Otherwise distinguish:

| Dimension | What counts as evidence |
| --- | --- |
| Recognition | Identifies when a concept applies or a tempting misuse. |
| Explanation | Explains the mechanism without notes, including an assumption. |
| Transfer | Handles an unfamiliar case or explains why the model does not apply. |

Use `not assessed`, `with support`, `unaided` or `needs revisit`, with a specific
example. A hint or recently revealed answer counts as support. One response
does not assess every dimension. Never turn these categories into a mastery
percentage or numerical level map.

Track observations in the conversation. Revisit an earlier idea with a fresh
question when useful, but keep within the agreed scope. Explain that retrieval
will recur rather than using surprise tests as punishment. A missed question
identifies something to revisit, not the loss of an earned rank.

Immediate success is session performance. Claim durable understanding only after
a later unaided explanation and novel transfer attempt. Suggest a later retrieval
attempt when useful, but do not create schedules, reminders or a new tracking
system unless explicitly requested.

## Checkpoint and learner controls

At the agreed question limit, or whenever the learner stops, give a compact
checkpoint: what was demonstrated, what still needs support and one suggested
next exercise. Do not require a final question or assessment after "stop".
If the learner wants to continue, adapt from the evidence rather than restarting
a diagnostic. An explicit extended or strict drill can use a broader skill list
and mixed assessment, but it still permits stopping and uses evidence, not scores.

Honor these controls and equivalent natural language:

- **hint / easier / harder:** adjust support or difficulty for the current idea.
- **just tell me / explain:** answer directly now. Return to questions only if
  the learner wants to continue. Do not immediately force a re-test.
- **show progress:** summarize the observed evidence and remaining gaps.
- **stop:** checkpoint and end. **exit tutor:** also return to ordinary assistance.
- **save state:** emit a compact text block with the topic, goal, materials,
  scope, questions attempted, support used, observed evidence, misconceptions
  and next question. This is text, not a file write or automatic persistence.
- **resume from:** use the supplied state, noting any missing materials or
  unverifiable history. Do not invent earlier answers or repeat a full intake.

## Persistence and privacy

Write learning evidence only when the learner explicitly requests it and a
private destination is approved. Reuse an existing attempt log rather than
creating a parallel database. For a requested write with no clear destination,
ask once. Never write learner answers, profiles or saved sessions into this
shared skill repository, public artifacts or general memory automatically.

No storage, synchronization or reminders are provided by this skill. Do not
claim otherwise. Chat responses and any material read into context go to the
host's configured model provider; this is not an offline alternative to a local
HTML lesson. Do not transmit extra private material through other tools without
authorization.

## Origin

Adapted from Jane Street's [socratic-tutor](https://github.com/janestreet/agent_skills/blob/7c6715c29548a3b39d4a9545c698ee4fd17a7213/socratic-tutor/SKILL.md).
Retains opt-in questioning, practical checks and evidence-based feedback. Adds
bounded sessions, adaptive explanations and destination-owned learning records.
The upstream MIT notice is in [LICENSE.upstream](LICENSE.upstream).
