# Architecture Decision Records

One file per significant decision: `NNNN-short-title.md`.

A decision belongs here when it was hard to reverse, or when the reasoning would otherwise
be lost and re-litigated later. Routine choices do not need a record.

## Format

```markdown
# NNNN. Title

**Status:** proposed | accepted | superseded by [NNNN](NNNN-...)
**Date:** YYYY-MM-DD

## Context

What forced a decision. Constraints, deadlines, what was already true.

## Decision

What was chosen, in the active voice.

## Consequences

What this makes easy, what it makes hard, and what it rules out.

## Alternatives considered

What else was on the table and why it lost.
```

The Phase 0 decisions are summarised in the decision log at the end of
[../architecture.md](../architecture.md). Promote any of them to a full record here if it
turns out to need the detail.
