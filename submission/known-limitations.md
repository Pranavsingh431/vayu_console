# Known limitations

Stated plainly, ranked by how much they should affect your assessment. Nothing here is
hedged — if a limitation is fundamental, it says so.

The exhaustive technical version is
[`docs/research/scientific-limitations.md`](../docs/research/scientific-limitations.md).

---

## Fundamental — cannot be fixed with more engineering

### 1. No ground truth for attribution exists

Delhi's regulatory network measures **mass concentration, not composition**. Nothing in this
system is validated against measured aerosol speciation, because none is collected.

This is why the system screens rather than apportions, and why no percentage or µg/m³
attribution appears anywhere. It is the single most important thing to understand about the
project.

### 2. Diwali is permanently confounded with stubble burning

They co-occur every year, in the same weeks, under the same meteorology. This is not a
sampling problem that more data resolves — the confound is structural.

The system addresses both hypotheses and separates neither. The structural argument that the
fire module cannot absorb fireworks (VIIRS overpasses fall outside the firework window) is an
argument from the satellite's orbit, and the test that would confirm it has not been run. The
engine reports that test as pending.

### 3. Traffic is weakly identified, and the LR is an upper bound

No signal exists outside the chemistry being explained — there is no satellite watching
Delhi's cars. The measured likelihood ratio is **2.11**, "weak" on the Kass & Raftery scale,
and the module is capped at MODERATE in code as a result.

Worse, 2.11 _over-credits_ traffic: the COVID lockdown also halted construction and industry,
so the ratio bounds the traffic-only effect from above rather than measuring it.

### 4. Industry is very weakly identified and carries no likelihood ratio

No natural experiment isolates industrial sources — COVID stopped traffic, construction and
industry simultaneously. The module therefore reports **no likelihood ratio at all** rather
than borrowing one.

SO₂ is measured at only **36 of 96** Delhi stations. At the remainder the module is
structurally blind, and absence of an SO₂ sensor is never reported as absence of industrial
influence.

---

## Methodological — choices that could reasonably have been made differently

### 5. The influence kernel is a modelling choice, not a calibrated physical model

Exponential distance decay, cosine upwind alignment, 24-hour linear recency. Results are
sensitive to it. It is not a dispersion model, and it is not tuned against measured transport.
The Challenge modal states this as an assumption on every fire-driven recommendation.

### 6. FRP is treated as a proxy for emissions

Fire Radiative Power measures radiated power, not smoke mass. The relationship is assumed
monotonic, not calibrated.

### 7. Single-station wind is assumed representative of a 200 km transport path

In reality wind veers with height and with distance. A single station's wind vector standing
in for the whole Punjab→Delhi trajectory is a real simplification, stated as an assumption
rather than buried.

### 8. Severity bands and the evidence are independent

Severity comes from the measured concentration against CPCB's published PM2.5 breakpoints —
deliberately _not_ derived from evidence strength. Evidence says which explanation is
plausible; it says nothing about how bad the air is. Judges sometimes expect these to be
linked; they are not, on purpose.

---

## Data coverage

### 9. The 2023–2024 archive gap

One station in 2023, two in 2024, against 50+ in adjacent years. **No trend may be drawn
across it.** This is a genuine archive gap, not a loading bug, and the console shows it rather
than interpolating.

### 10. Sampling is irregular, not hourly

Station reporting cadence varies. "Station-hour" is a normalisation, not a native unit of the
data.

### 11. Live and archived readings are not the same measurement

The live feed is provisional and later revised. Mixing the two silently would corrupt any
comparison — which is one reason the console replays archived incidents rather than running
live.

### 12. Cloud cover suppresses fire detection when it matters most

During heavy winter haze the satellite may under-report exactly when the question is most
urgent. Flagged as a limitation, not worked around.

---

## Scope

### 13. Delhi only

The evidence modules are Delhi-calibrated. The architecture ports to other cities; the
likelihood ratios do not — each would need its own natural experiments re-run. Reusing LR 2.11
elsewhere would be an unearned transfer.

### 14. The console replays history and does not run live

Deliberate: live data cannot validate a reasoning system. The pipeline supports live
ingestion; the validation story does not benefit from it.

### 15. GRAP has no scenario

GRAP is a threshold-triggered regulatory regime, not a dated event, so there is no single
station-hour to reconstruct. It is shown in the UI as unavailable with that reason, because
fabricating an episode to fill the slot would undermine everything else here.

### 16. Odd-Even I and III are unanalysed

Both are confounded — Odd-Even I by winter inversion (and two-wheeler/CNG exemptions),
Odd-Even III by peak stubble season. They are listed as **PENDING** in the validation timeline
rather than quietly dropped.

### 17. The system does not forecast

It offers reassessment windows ("reassess within 6 hours", with the reason), never predicted
concentrations. It **cannot estimate the effect of any action it recommends**, and the
recommendation panel says so.

### 18. Desktop only

Designed for a control-room screen at 1440×900 and above. Mobile is not supported and is not
claimed to be.
