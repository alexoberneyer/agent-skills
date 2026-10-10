---
name: build-learning-artifact
description: Build or revise a self-contained interactive HTML lesson for a scientific or mathematical concept, with experiments, explanations, and transfer exercises. Use for learning artifacts, not slide decks or general websites.
---

# Build a learning artifact

Deliver a lesson that helps the learner predict, explain, and apply a mechanism.
The artifact should open directly from disk with no installation or network.

## Establish the learning contract

Read the destination's instructions and existing examples. If available, read its
learner profile and curriculum. Keep these private inputs in the destination;
never copy them, local paths, or personalized outputs into a shared skill repo.
Use user-provided preferences without inferring diagnoses or fixed learning styles.

Choose a bounded concept, prerequisites, and observable outcomes: what can the
learner explain or solve afterward? Identify the misconception the experiment
should expose. Follow established paths and language. Ask only when missing
information materially changes the lesson; otherwise state reasonable defaults.

## Design for reasoning

Build a coherent sequence, adapting its shape to the concept:

1. A concrete prediction before its answer, with an explicit way to skip.
2. A manipulable model that exposes the mechanism. Give one-variable experiments
   and require a prediction or explanation, not aimless slider movement.
3. A concise explanation connecting the visual, quantities, and equations.
4. Applications in meaningfully different domains. State where each analogy ends.
5. Retrieval without hints and at least one novel transfer problem, followed by
   worked feedback and a rubric. Keep answers hidden until requested.

Separate recognizing terminology, explaining a mechanism, and transferring it.
Opening the artifact or revealing answers is not evidence of mastery. Suggest a
later retrieval attempt, but create reminders or schedules only when requested.

## Scientific contract

Verify central claims with credible primary or authoritative teaching sources.
Link sources near the relevant explanation or in an annotated source list.
Distinguish established results, modeling assumptions, illustrations, and uncertain
empirical claims. Use original examples and comply with source quotation limits.

Define every variable, unit, denominator, and valid range. Explain assumptions,
boundary cases, and what the model omits. Label synthetic data and expected counts.
Do not imply simulated output is a measurement. Do not turn analogy into causal
evidence or uncertainty into a precise fact.

Derive and independently calculate at least one worked example. Test limiting
cases, invariants, and undefined outputs. Preserve precision in calculations and
round only for display. For stochastic models, distinguish expected from sampled
results and make validation reproducible. Never invent citations.

## Implementation contract

Use a complete HTML document with a language, title, and viewport. Inline CSS,
JavaScript, diagrams, and required assets. Prefer native controls and inline SVG.
Avoid external fonts, libraries, APIs, telemetry, build steps, and service workers.
External reference links may require a connection; the lesson must not.

Use semantic headings and landmarks, explicit control labels, visible keyboard
focus, sufficient contrast, and text/table equivalents for essential graphics.
Do not encode meaning only by color. Make touch controls practical, reflow on
small screens and at zoom, respect reduced motion, and avoid automatic animation.
Use a concise live announcement or output for changing results. Provide a reset.
Keep the explanation and a worked example readable with JavaScript disabled.

Keep math readable offline, using text or native MathML with an accessible
explanation. Use a pure calculation function when the model warrants tests.
Explain whether responses persist. If storage is needed, handle denied/unavailable
storage gracefully and provide explicit clearing; never imply cross-device sync.

## Validate and deliver

Use available browser tools to exercise every control and reset. Check console
errors, keyboard operation, narrow and wide layouts, and network-free use. Inspect
screenshots, not only source. Check links and mathematical results independently.
Add focused reproducible tests when calculations or interaction states justify them.
Report checks that were unavailable rather than claiming them passed.

If a registry exists, update only this artifact's build/review evidence and links.
Leave learner assessments unchanged unless the learner supplies evidence. If a
separate review is requested, use `review-learning-artifact` when available or
perform an explicitly labeled self-review. Building never authorizes publication.
Return the artifact location, verification, assumptions, and material limitations.
