# Prompts and audience exercises

These prompts structure a workflow; they do not guarantee correctness. Use approved inputs and independently review consequential outputs. This is original material, not extracted from the empty `claude_research/prompts.md` file.

## Evidence-aware literature assistant

```text
Question: [bounded research question]
Use only the supplied papers and approved sources.
For each material claim, provide the source title, identifier and supporting location.
Separate author reports, independent replication, interpretation and unanswered questions.
Do not invent references or fill missing evidence with a confident guess.
Compare assumptions and populations before comparing numerical results.
Finish with a list of claims that a human reviewer should verify.
```

Reviewer task: open three consequential citations, inspect assumptions and check whether each source supports the associated statement. A valid title alone is insufficient.

## Engineering alternative comparison

```text
Goal: compare [alternatives] against [approved specification].
State input values, units, loading conditions and boundary assumptions.
Mark missing data. Link factual properties to supplied evidence.
Identify infeasible options before comparing benefits.
Return a table of tradeoffs and the checks needed before design acceptance.
Do not authorize procurement or deployment.
```

Reviewer task: recompute a representative case, inspect a boundary case and compare with an existing trusted method.

## Focused software change

```text
Issue: [specific requirement and observed failure]
Scope: [allowed files and tools]
First inspect the relevant code and explain the proposed change.
Implement the smallest coherent fix.
Run meaningful checks for the behavior that could fail.
Report the result, limitations and required maintainer review.
Stop if the task requires access beyond the stated scope.
```

Reviewer task: inspect whether tests exercise the actual requirement, whether the change handles important edge cases and whether it integrates into the repository.

## Competing mechanisms

```text
Observations: [approved measurements]
Candidate mechanisms: [A and B]
List what each mechanism predicts and which assumptions it uses.
Preserve both if current evidence cannot distinguish them.
Suggest feasible perturbations for a domain expert to review.
For each perturbation, identify observable outcomes that would differ.
Separate prediction uncertainty, measurement noise and mechanistic ambiguity.
```

Reviewer task: determine whether the perturbation is feasible, appropriate and capable of distinguishing the candidates. This is concept formation, not authorization to run a laboratory procedure.

## Decision brief

```text
Prepare a brief from this approved document set.
Use headings for decision, evidence, alternatives and unresolved assumptions.
Link every material factual claim to its supporting source.
Mark information absent from the documents as unknown.
Include reasons that could change the recommendation.
Identify the claims the decision owner must check before acting.
```

Reviewer task: inspect whether a critical omission or unsupported premise changes the decision.

## Audience exercise A: evidence labels, 45 seconds

Show three statements:

1. “An organization published a manuscript and a proof repository.”
2. “The mathematical community has accepted the theorem.”
3. “Our factory will benefit from this result next quarter.”

Ask what evidence each needs. The correct teaching point is that publication does not automatically establish either acceptance or commercial benefit. No audience data collection is required.

## Audience exercise B: net effort, 30 seconds

Use the site’s calculator. Keep baseline at 60 minutes, assumed drafting saving at 40%, correction at 5 minutes and volume at 10 tasks/week. Increase review from 10 to 25 minutes. Net weekly savings move from +1.5 hours to −1 hour. Label these as assumed inputs. Ask which component their organization currently measures.

## Audience exercise C: one pilot, 60 seconds

Privately complete: “In my field, AI could help with ____. A result is acceptable only if ____. The accountable owner is ____. We will measure ____.” Invite one sanitized answer if the schedule permits. Do not ask attendees to share confidential work.

## Rehearsal choice

Use at most two brief interactions during the scheduled talk. The final slide has room for a short response or handoff. Extended demonstrations and panel discussion belong outside the timed script or require trimming spoken material.
