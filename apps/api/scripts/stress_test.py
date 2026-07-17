#!/usr/bin/env python
"""Falsification tests for the Evidence Engine's hypothesis modules.

These are written so that they can FAIL. A module that fails is deleted from the
product, not reinterpreted — see docs/research/inference.md §5.7.

Falsification needs no minimum n. One decisive test kills a hypothesis, which is
why n≈6 events is useless for training a classifier (§4) and sufficient here.

    python scripts/stress_test.py covid

The COVID test is the sharp one. Lockdown stopped traffic, construction and much
industry — but power generation was essential and kept running. So it is a
*differential* intervention, and yields a prediction that discriminates:

    If NO2 tracks traffic and SO2 tracks power generation,
    the NO2/SO2 ratio MUST collapse during lockdown.

If it does not, NO2 is not a traffic-specific proxy in Delhi and the vehicle
module is deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import dispose_engine, get_session_factory

# India's national lockdown began 24 Mar 2020. The baseline is the weeks
# immediately before it, so season and meteorology differ as little as possible.
LOCKDOWN_START = dt.date(2020, 3, 24)
BASELINE = (dt.date(2020, 3, 1), dt.date(2020, 3, 23))
LOCKDOWN = (dt.date(2020, 3, 25), dt.date(2020, 4, 30))

# Kass & Raftery (1995) evidence bands, applied to a likelihood ratio.
BANDS = [
    (1, 3, "weak", "★"),
    (3, 10, "substantial", "★★"),
    (10, 30, "strong", "★★★"),
    (30, 100, "very strong", "★★★★"),
    (100, float("inf"), "decisive", "★★★★★"),
]


def band(lr: float) -> tuple[str, str]:
    lr = max(lr, 1 / lr) if lr > 0 else 1.0
    for lo, hi, label, stars in BANDS:
        if lo <= lr < hi:
            return label, stars
    return "weak", "★"


async def series(session, parameter: str, a: dt.date, b: dt.date) -> list[float]:
    """Station-hour means for a pollutant over a window. Sentinels excluded."""
    rows = (
        await session.execute(
            text("""
        select avg(value) v
        from measurements
        where parameter = :p
          and value >= 0                 -- -999 sentinels and instrument errors
          and measured_at >= :a and measured_at < :b
        group by station_id, date_trunc('hour', measured_at)
        """),
            {"p": parameter, "a": a, "b": b},
        )
    ).all()
    return [float(r.v) for r in rows if r.v is not None]


async def covid_test() -> int:
    async with get_session_factory()() as s:
        print("=" * 78)
        print("STRESS TEST — vehicle module, COVID lockdown 2020")
        print("=" * 78)
        print(f"  baseline : {BASELINE[0]} .. {BASELINE[1]}  (traffic normal)")
        print(f"  lockdown : {LOCKDOWN[0]} .. {LOCKDOWN[1]}  (traffic ~0 by order)")
        print()

        out: dict[str, tuple[float, float, int, int]] = {}
        for p in ("no2", "so2", "pm25", "co"):
            base = await series(s, p, *BASELINE)
            lock = await series(s, p, *LOCKDOWN)
            if len(base) < 30 or len(lock) < 30:
                print(f"  {p:5s} INSUFFICIENT DATA  base n={len(base)} lock n={len(lock)}")
                continue
            mb, ml = statistics.median(base), statistics.median(lock)
            out[p] = (mb, ml, len(base), len(lock))
            change = (ml - mb) / mb * 100 if mb else 0
            print(
                f"  {p:5s} median {mb:7.1f} -> {ml:7.1f}   {change:+6.1f}%"
                f"   (n {len(base):,} -> {len(lock):,})"
            )

        if "no2" not in out or "so2" not in out:
            print("\n  VERDICT: UNCERTAIN — insufficient data to run the test.")
            return 2

        print()
        print("-" * 78)
        print("TEST 1 — does NO2 fall when traffic stops?")
        no2_b, no2_l = out["no2"][0], out["no2"][1]
        no2_drop = (no2_b - no2_l) / no2_b * 100
        t1 = no2_drop > 20
        print(f"  NO2 fell {no2_drop:.1f}%   -> {'PASS' if t1 else 'FAIL'} (needs >20%)")

        print()
        print("TEST 2 — does the NO2/SO2 ratio collapse?")
        print("  (power generation stayed essential, so SO2 should hold up.")
        print("   if the ratio holds, NO2 is not traffic-specific.)")
        r_b = out["no2"][0] / out["so2"][0]
        r_l = out["no2"][1] / out["so2"][1]
        lr = r_b / r_l if r_l else float("inf")
        label, stars = band(lr)
        print(f"  NO2/SO2  {r_b:.2f} -> {r_l:.2f}   ratio-of-ratios (LR) = {lr:.2f}")
        print(f"  evidence: {label} {stars}   (Kass & Raftery bands)")
        t2 = lr > 1.5
        print(f"  -> {'PASS' if t2 else 'FAIL'} (needs LR > 1.5)")

        print()
        print("=" * 78)
        if t1 and t2:
            v = "ACCEPTED"
            why = (
                "NO2 fell sharply while SO2 held up. NO2 carries traffic-specific "
                "information in Delhi. The vehicle module survives -- with the "
                "caveat that lockdown also stopped construction and industry, so "
                "the LR is an upper bound on the traffic-only effect."
            )
        elif t1 and not t2:
            v = "WEAKENED"
            why = (
                "NO2 fell, but so did SO2 -- the ratio did not move. The fall is "
                "consistent with 'all activity stopped', not with traffic "
                "specifically. NO2 cannot separate traffic from industry here."
            )
        else:
            v = "REJECTED"
            why = (
                "NO2 did not fall materially when traffic went to ~0. It is not a "
                "traffic proxy in Delhi. Per inference.md §5.7 the vehicle module "
                "is deleted from the product and this test written up in "
                "scientific-limitations.md."
            )
        print(f"VERDICT: vehicle module {v}")
        print()
        for line in _wrap(why, 76):
            print(f"  {line}")
        print("=" * 78)
        return 0


def _wrap(s: str, w: int) -> list[str]:
    words, out, cur = s.split(), [], ""
    for word in words:
        if len(cur) + len(word) + 1 > w:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        out.append(cur)
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("test", choices=["covid"])
    args = parser.parse_args()
    try:
        return await covid_test() if args.test == "covid" else 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
