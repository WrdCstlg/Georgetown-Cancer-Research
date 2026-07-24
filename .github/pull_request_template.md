<!--
  Definition of done: AGENTS.md §4. Every field is required.
  The Spec item field is enforced in CI (job `spec-id`): a PR body with no SPEC-NNN reference fails the check.
-->

## Spec item
SPEC-NNN — <title as listed in SPEC.md>. If the work is new, its spec item was added to SPEC.md BEFORE code (I6).

## Layer / concern
<pipeline | core | producers | query | interface | contracts | repo tooling> — one concern per PR; if it spans layers it is too big or it is a contract change (AGENTS.md §5).

## Blast radius
<files/layers touched and downstream impact. Contract (`contracts/`) changes: flag explicitly and list every downstream layer they touch.>

## Acceptance criteria
<the executable checks from the SPEC.md item this PR satisfies — checks, not narration (I2)>

## Execution artifact
<pasted test / type-check / run output proving the above — G3. No artifact ⇒ SPECIFIED, not FUNCTIONAL.>

## Golden fixtures
<"fixtures pass" — or the justification for any altered fixture output (G4)>

## Decision records
<D-NNN entries logged in docs/DECISIONS.md for any fork resolved — I4 — or "none">
