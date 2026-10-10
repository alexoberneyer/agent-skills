---
name: review-learning-artifact
description: Review an interactive HTML learning artifact for scientific correctness, useful learning exercises, accessibility, and offline functionality. Use before accepting a lesson or when checking an existing learning module.
---

# Review a learning artifact

Read the artifact, relevant destination instructions, intended outcomes, and any
existing validation evidence. Review without editing unless fixes are requested.
Do not publish the artifact or send private content to external services.

## Check the scientific model

- Verify central claims against primary or authoritative sources. Inspect cited
  passages and check that they support the claim, not merely the general topic.
- Independently derive the formulas and recalculate examples. Do not validate
  code by copying its formula into a second implementation of the same mistake.
  Use hand-worked counts, exhaustive enumeration, or a different derivation.
- Check units, denominators, assumptions, domains, precision, and conservation or
  normalization invariants. Probe zero, extremes, impossible observations, and
  degenerate inputs. For randomness, separate sampling error from model errors.
- Check that visuals, text, tables, and answers agree. Expected counts may be
  fractional; rounded symbols must not masquerade as exact observations.
- Distinguish theorem from empirical claim and analogy from mechanism. Identify
  where a model stops applying, including selection effects or dependent evidence.

## Check the learning experience

Try the lesson as a learner. Is there a prediction before feedback? Does changing
an input clarify a mechanism? Can the learner connect the visual to the equation?
Are prerequisites sufficient and important terms defined?

Solve retrieval and novel transfer questions without their answer keys first.
Then verify feedback and rubrics. A renamed version of the worked example tests
near transfer; also include a change in assumptions or a judgment about model use.
Do not treat engagement, confidence, or answer reveals as demonstrated mastery.

## Check the artifact

Open it directly from disk when supported and with external network unavailable.
Inspect required assets, network requests, console errors, relative links, and
any persistence claims. The lesson should not depend on a CDN or account.

Exercise controls, valid extremes, invalid typed inputs, reveal/skip flows, and
reset. Check logical tab order, labels, focus visibility, screen-reader structure,
non-color cues, reduced motion, small-screen reflow, and enlarged text. Ensure
essential visuals have text alternatives. Read the fallback with JavaScript off.
Inspect actual browser renders at narrow and wide sizes. Automated accessibility
checks complement manual review; they do not certify accessibility compliance.

Use available test tools without imposing a new framework on the destination.
State the browser, viewport sizes, cases tested, and gaps. If browser or assistive
technology testing is unavailable, say so and reduce the readiness claim.

## Report actionable findings

Lead with readiness: ready for learner trial, ready with limitations, or needs
correction. Give each finding a location, observable problem, learning impact,
and proposed fix. Prioritize incorrect science, misleading feedback, and blocked
access before visual polish. Separate verified findings from uncertain concerns.

Summarize scientific, learning, and functional evidence. Distinguish author
self-review from independent review. A successful review is not learner mastery.
Update a registry only if requested, preserving its format and learner history.
