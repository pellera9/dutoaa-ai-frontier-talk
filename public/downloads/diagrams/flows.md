# Editable flows

## The discovery loop

Conceptual workflow: proposals become useful through evidence and accountable decisions.

```mermaid
flowchart LR
  A[Meaningful problem] --> B[AI-supported proposals]
  B --> C[Independent checks]
  C --> D[Human interpretation]
  D --> E[Action and learning]
  E --> A
```

## A bounded research agent

Tool access and a stopping condition are explicit parts of the system.

```mermaid
flowchart LR
  A[Goal and permissions] --> B[Model proposes action]
  B --> C[Bounded tool execution]
  C --> D[Observe evidence]
  D --> B
  D --> E[Review or stop]
```

## Questions for evaluating a claim

Different disciplines use different acceptance standards. These are questions, not a universal linear ranking.

```mermaid
flowchart LR
  A[Who reported it?] --> B[What exact claim?]
  B --> C[Which artifacts?]
  C --> D[What independent checks?]
  D --> E[What acceptance standard?]
```

## Preserve the mathematical scope

Interpretation guide; this package does not certify a mathematical proof.

```mermaid
flowchart LR
  A[Exact equation] --> B[Initial data and forcing]
  B --> C[Claimed conclusion]
  C --> D[Audit formal statement and assumptions]
  D --> E[Independent scrutiny]
```

## Verification gate

Use checks capable of rejecting a generated result; select the reviewer and criteria before acting.

```mermaid
flowchart LR
  A[Acceptance criteria] --> B[Generate candidate]
  B --> C[Run meaningful checks]
  C --> D[Accountable review]
  D --> E{Accept?}
  E -->|Yes| F[Use with monitoring]
  E -->|No| B
```

## Distinct scientific questions

A shape prediction does not by itself identify function, mechanism or therapeutic benefit.

```mermaid
flowchart LR
  A[Structure: what shape?] --> B[Function: what effect?]
  B --> C[Mechanism: what process?]
  C --> D[Intervention: what changes?]
  D --> E[Outcome: useful and safe?]
```

## Generic drug discovery evidence gates

A simplified educational pipeline; stages and regulatory requirements differ by product and jurisdiction.

```mermaid
flowchart LR
  A[Target hypothesis] --> B[Candidate design]
  B --> C[Laboratory evidence]
  C --> D[Clinical evidence]
  D --> E[Regulatory assessment]
  C -->|Revise or stop| B
  D -->|Revise or stop| B
```

## Wave Intelligence: proposed mechanism workflow

Original explanatory adaptation of Liu’s repository perspective, pp. 3–6; a research agenda, not an established validated system.

```mermaid
flowchart LR
  A[Text + structures + measurements] --> B[Shared latent state]
  B --> C[Dynamics under conditions and interventions]
  C --> D[Observable predictions]
  D --> E[Compare candidate mechanisms]
  E --> F[Discriminating experiment]
  F --> A
```

## Candidate search with an evaluator

Conceptual abstraction of tool-connected discovery; simulation and physical validation can have different requirements.

```mermaid
flowchart LR
  A[Objective and constraints] --> B[Propose candidates]
  B --> C[Evaluator]
  C --> D[Keep useful results]
  D --> B
  D --> E[Independent acceptance]
```

## Measure complete software work

Generation time is only one component. Acceptance includes review and integration.

```mermaid
flowchart LR
  A[Specify change] --> B[Draft patch]
  B --> C[Test and inspect]
  C --> D[Correct and integrate]
  D --> E[Measure total time and defects]
```

## Grounded knowledge work

The final decision owner checks material claims and the completeness of the evidence.

```mermaid
flowchart LR
  A[Approved documents] --> B[Source-linked draft]
  B --> C[Check material claims]
  C --> D[Decision owner review]
  D --> E[Measure usefulness]
```

## Choose a pilot inside your domain

Illustrative suggestions for alumni; no claims about an existing DUT alumni program.

```mermaid
flowchart LR
  A[Domain problem] --> B[Bounded AI task]
  B --> C[Credible evaluator]
  C --> D[Human owner]
  D --> E[Measured pilot]
```

## A durable skill portfolio

Recommended capabilities to practice together, rather than a forecast of job counts.

```mermaid
flowchart LR
  A[Frame problems] --> B[Inspect evidence]
  B --> C[Evaluate and integrate]
  C --> D[Explain decisions]
  D --> E[Keep learning]
  E --> A
```

## Match autonomy to consequence

Suggested decision aid, not a numeric risk model or legal determination.

```mermaid
flowchart LR
  A[Task and data] --> B[Consequences of error]
  B --> C[Strength of evaluator]
  C --> D[Set bounded permissions]
  D --> E[Monitor and escalate]
```

## A 30-day alumni pilot

Recommended schedule. Expand, revise and stop are all legitimate outcomes.

```mermaid
flowchart LR
  A[Week 1: task and baseline] --> B[Week 2: workflow and controls]
  B --> C[Week 3: matched comparison]
  C --> D[Week 4: review evidence]
  D --> E[Expand / revise / stop]
```

## From a paper to a checked prototype

An educational audit: derivatives checked, two claims need correction, and synthetic comparisons do not establish a production winner.

```mermaid
flowchart LR
  A[Read the paper] --> B[Preserve assumptions]
  B --> C[Build the prototype]
  C --> D[Check equations]
  D --> E[Qualify conclusions]
  D --> B
```
