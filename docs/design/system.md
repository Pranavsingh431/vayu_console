# Design System

> The console an officer opens at 2am during a severe episode.

## Principles

1. **Colour is information, never decoration.** The palette is nearly monochrome so
   that when something turns red it _means_ something. There is no brand colour
   competing with the severity signal.
2. **The layout is the workflow.** Situation → Map → Evidence → Decision, left to
   right, top to bottom. An officer reads it in the order the reasoning happens.
3. **The page never scrolls.** Panels scroll. On a control-room screen, scrolling the
   page means losing the number you were looking at.
4. **Absence is stated, never implied.** Empty states explain _why_ they are empty.
   "No data" is never shown, because a blank panel and a blind sensor look identical.

## Palette

Black-only. No light mode, no toggle.

| Token             | Value     | Use                            |
| ----------------- | --------- | ------------------------------ |
| Background        | `#000000` | The page                       |
| Primary surface   | `#0A0A0A` | Panels                         |
| Secondary surface | `#111111` | Nested surfaces, expanded rows |
| Border            | `#1C1C1C` | Every division                 |
| Primary text      | `#FFFFFF` | Values, titles                 |
| Secondary text    | `#A1A1AA` | Supporting prose               |
| Muted text        | `#71717A` | Labels, footnotes              |
| Success           | `#22C55E` | Cleared, calibrated            |
| Warning           | `#EAB308` | Human review, partial data     |
| Critical          | `#EF4444` | Severe, fires, gaps            |

Nothing else. Primary is white-on-black.

## Type

Geist Sans, Geist Mono for values. **Tabular numerals globally** — an officer compares
1288 to 612 at a glance, and proportional digits make that harder than it needs to be.

## Radius & elevation

6px (`--radius: 0.375rem`). No shadows, no glows. Depth comes from surface steps.

## Motion

150–250ms, ease-out. Present, never noticed. `prefers-reduced-motion` disables all of
it. No bouncing, no spring.

## Components

```
ConsoleView                     layout, data, presentation state
├── SituationHeader             the number and its context
├── ScenarioBar                 Demo Mode + Present Incident
├── PresentationProgress        hairline, no chrome
├── StationMap                  SVG transport geometry
├── EvidencePanel               per-hypothesis, expandable
│   └── EvidenceRow
├── RecommendationPanel
│   ├── ChallengeDialog         the signature feature
│   └── ExpectedImpact
└── Timeline                    historical validation
```

## Accessibility

- Keyboard: every control is a real `<button>`; tabs use `role="tab"` + `aria-selected`.
- Focus: 2px ring, offset, always visible. Never removed.
- Escape exits Presentation Mode — a presenter must never lose control of the screen.
- The map carries an `aria-label` describing wind and fire count, because an SVG of
  the argument is useless to a screen reader without it.
- Contrast: `#A1A1AA` on `#0A0A0A` ≈ 9:1. `#71717A` is reserved for labels, never for
  anything load-bearing.

## Known limitations

- **Desktop only.** 16:9 primary, laptop secondary. Mobile is not supported and the
  three-column grid will not reflow.
- **The map is a schematic**, not a GIS view. It has no basemap, no zoom, no pan. It
  draws the transport geometry because that is the argument; a street map would be
  decoration.
- **Fires are drawn as one aggregate** in the upwind sector, not at true coordinates.
  The module reasons over total wind-weighted influence, and plotting 1,593 pixels
  would imply a precision it does not use.
- **Timeline events are not clickable.** They highlight with the active scenario but do
  not drive selection — the three scenarios in the bar are the ones with ingested data.
