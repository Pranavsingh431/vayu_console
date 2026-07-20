# Submission materials

Everything a judge or reviewer needs, in the order it is most useful.

| Document                                               | Read it for                                                                                                                                                       |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [technical-document.pdf](technical-document.pdf)       | **The main submission item.** 18 pages: architecture, evidence engine maths, validation, limitations. Source: [`technical-document.tex`](technical-document.tex). |
| [final-presentation.pdf](final-presentation.pdf)       | The 13-slide deck, also as [.pptx](final-presentation.pptx).                                                                                                      |
| [demo-script.md](demo-script.md)                       | The five-minute walkthrough, timed.                                                                                                                               |
| [judge-faq.md](judge-faq.md)                           | Hard questions and their answers, including the ones we expect to be challenged on.                                                                               |
| [pitch-outline.md](pitch-outline.md)                   | Ten-slide structure with speaker notes.                                                                                                                           |
| [scientific-methodology.md](scientific-methodology.md) | Why this is screening rather than apportionment, and what that buys.                                                                                              |
| [technical-highlights.md](technical-highlights.md)     | The engineering findings worth a reviewer's time.                                                                                                                 |
| [known-limitations.md](known-limitations.md)           | What the system cannot do, stated plainly.                                                                                                                        |

Screenshots live in [`../docs/assets/screenshots/`](../docs/assets/screenshots/) and are
captured from the running application by `npm run screenshots --workspace apps/web`. They are
not mockups.

Architecture diagrams are Mermaid, rendered inline in the
[root README](../README.md#architecture) so they never drift from the prose around them.

## The one-sentence version

> Most systems are designed to always give an answer. Vayu Console is designed to give an
> answer only when the evidence can support one — and to show exactly why.

## Canonical sources

These documents summarise; they do not duplicate. Where a claim has a primary source in the
repository, it links there rather than restating it:

- Inference design and the rejected classifier — [`docs/research/inference.md`](../docs/research/inference.md)
- Scientific limitations, in full — [`docs/research/scientific-limitations.md`](../docs/research/scientific-limitations.md)
- Station coverage and the archive gap — [`docs/research/station_inventory/coverage.md`](../docs/research/station_inventory/coverage.md)
- Evidence Engine design — [`docs/architecture/evidence-engine.md`](../docs/architecture/evidence-engine.md)
- Decision Engine design — [`docs/architecture/decision-engine.md`](../docs/architecture/decision-engine.md)
- Deployment — [`docs/deployment.md`](../docs/deployment.md)
