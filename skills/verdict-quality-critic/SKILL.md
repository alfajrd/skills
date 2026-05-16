---
name: verdict-quality-critic
description: Use when an LLM generates structured judgment output (evaluations, scored reviews, multi-axis verdicts) and the response needs to pass both schema validation and a Reflexion-style critic rubric covering accuracy, voice consistency, safety guardrails, and respect for user-declared constraints.
---

# Verdict Quality Critic

## Overview

A two-gate pipeline wrapping an LLM call that produces structured judgments or evaluations:

1. **Schema validation** against the expected output structure
2. **Reflexion-style critic pass** that revises the output against an explicit rubric covering accuracy, voice, safety, and user-constraint respect

Use this pattern whenever raw model output is too unreliable to ship — for example, when the LLM is asked to evaluate, score, judge, or critique something on a user's behalf and the result is presented as a finished artifact.

## When to Use

- Backend pipelines where an LLM produces a structured judgment (scored review, multi-axis evaluation, ruling, recommendation)
- Outputs presented to end users as a finished verdict rather than raw model text
- Mixed-criteria evaluations where multiple axes are scored independently

Do NOT use for:
- UI / display formatting (the critic operates on validated JSON, not on rendered output)
- Upstream classification / routing (run those before this pipeline)
- Deterministic lookups that don't need an LLM at all

## Failure Modes

The rubric below catches six distinct failure modes that schema validation alone cannot catch:

| Failure | Severity | Why it matters |
|---|---|---|
| **User-constraint violation** | HIGH | Output references items the user declared off-limits (allergens, blocked topics, dietary rules, etc.). Brand-trust breach. |
| **Safety-gate breach** | HIGH | Output applies harsh / blame vocabulary to a case the safety gate should soften. |
| **Rubric misapplication** | HIGH | Output scores on a metric the user didn't select OR praises on a metric the user wanted minimized. |
| **Voice register drift** | MEDIUM | Output drifts out of the intended persona — too warm, too clinical, too casual. |
| **Out-of-scope critique** | HIGH | Output critiques the user (identity, body, worth, character) instead of the subject being evaluated. |
| **Axis missing** | MEDIUM | Output scores some axes but silently drops others — partial judgments feel half-baked. |

## Pipeline

```
Generate (structured-output library + JSON schema)
     ↓
Validate (Pydantic / equivalent)   — auto-retry on schema fail
     ↓
Critic pass (rubric below)         — revise on fail, max 2 iterations
     ↓
Final validated output
```

## The Rubric

Each generated output MUST pass every check below. The critic LLM applies them and revises any failures. Checks marked **HARD SAFETY** cannot be skipped or softened under any condition.

| Check | Rule |
|---|---|
| **User-constraint respect (HARD SAFETY)** | Output text contains ZERO items from the user's declared exclusion / block list. Mandatory revision if any reference appears. |
| **Safety gate (HARD SAFETY)** | If the input falls below a domain-specific threshold (small portion, low-risk case, sub-clinical severity, etc.), the output MUST NOT apply the harsh-judgment vocabulary reserved for above-threshold cases. A neutral verdict replaces the harsh one. |
| **No out-of-scope critique (HARD SAFETY)** | The output critiques the *subject being evaluated*, never the user's identity, body, worth, or character. |
| **Rubric application** | The judgment respects the user's selected criteria. If the user picked criterion X, the output scores on X — never the inverse, never absent. |
| **All axes present** | Every required scoring axis is evaluated in the output, even briefly. FAIL if any required axis is silently dropped. |
| **Voice register** | Output reads in the intended persona (defined per-app). FAIL on phrases that break character. |
| **Persona consistency** | Output references the user's `personaLabel` field where the schema requires it. |
| **Numeric band** | Any stated numeric estimate stays within ±X% of the ground-truth upstream value (if one exists). The LLM cannot invent a number when an authoritative one was passed in. |
| **No prohibited claim** | The output does not make claims outside its declared scope (no medical / legal / financial claims unless that is the app's purpose). |

When adapting this rubric to a specific app, replace the placeholders:
- *exclusion / block list* → the actual user-profile field
- *domain-specific threshold* → e.g., min portion, max risk, min severity
- *intended persona* → e.g., "judicial, theatrical, brutal" / "warm, conversational, calm"
- *prohibited claim* → categories your app must not produce

## Critic Prompt Template

```
You are critiquing a generated <output-type> against an explicit rubric for the <app-name> app. For each numbered check, output PASS or FAIL with a one-line reason. Checks 1, 2, and 3 are HARD SAFETY checks — they cannot be skipped or softened.

1. User-constraint respect (HARD SAFETY): Does the output reference any item from the user's exclusion list?
2. Safety gate (HARD SAFETY): If the input is below the safety threshold, does the output avoid the harsh-judgment vocabulary?
3. No out-of-scope critique (HARD SAFETY): Does the output critique only the subject, never the user's identity / body / character?
4. Rubric application: Does the judgment respect the user's selected criteria?
5. All axes present: Are all required axes judged?
6. Voice register: Does the output sound like the intended persona?
7. Persona consistency: Is the persona / agent label referenced where the schema requires it?
8. Numeric band: Is any numeric estimate within ±X% of the upstream ground-truth value?
9. No prohibited claim: Does the output avoid claims outside its declared scope?

If any check FAILs, output the corrected JSON that fixes every failure. If all PASS, output the original output unchanged.

Output to critique:
<output JSON>

Inputs were: <upstream ground-truth value, user profile (exclusions, criteria, personaLabel)>
```

## Schema

See [`schema.example.json`](./schema.example.json) for a minimal example schema. Adapt the fields to your domain — the critic pattern doesn't care what the fields are, only that there is a schema and a rubric to enforce.

## Common Mistakes

- **Forgetting the safety gate.** A case below your threshold should never get the above-threshold treatment. The gate catches this on the relevant axis specifically; other axes can still be evaluated normally.
- **Soft critic prompts** ("does this look reasonable?") instead of explicit PASS/FAIL per rubric item — the rubric must be specific or the critic gives the model a pass.
- **Forgetting to thread user constraints into the critic.** Without the user profile, the critic can't tell whether the judgment is correctly tailored.
- **Inverting praise and critique** when the user picks no specific criteria — fall back to a generic rubric that still produces sensible judgments, not random ones.

## Iteration Notes

Production telemetry to track:
- Critic FAIL rate per rubric item — high rates suggest the generation prompt is weak on that axis
- Human-override rate — frequent "wrong" reports indicate the rubric needs additional checks
- Safety-gate trigger distribution — to verify the threshold is calibrated

Expand baseline coverage as production data reveals which categories most need extra rubric checks.
