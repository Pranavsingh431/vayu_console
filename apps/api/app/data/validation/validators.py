"""Validation for measurement series.

Designed around what the archive actually contains, not what the spec assumed.

The important one: **sampling is irregular, not hourly.** Observed timestamps run
00:15, 00:30, 01:00, 01:30, 02:00, 02:15, 02:45 — uneven gaps are normal. A
validator demanding a reading every hour reports every station as broken and
teaches you to ignore it. So this reports the *observed* interval and completeness
against it, and never invents a grid.

Nothing here drops data. It describes; the caller decides.
"""

from __future__ import annotations

import datetime as dt
import itertools
import statistics
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

# Physically impossible or instrument-error values. Deliberately generous: the aim
# is to catch nonsense (negative mass, stuck sensors), not to quietly discard the
# extreme-but-real readings that are the entire subject of this project. Delhi
# genuinely records PM2.5 above 900 µg/m³ on Diwali night.
PLAUSIBLE_RANGE: dict[str, tuple[float, float]] = {
    "pm25": (0.0, 2000.0),
    "pm10": (0.0, 3000.0),
    "no2": (0.0, 1000.0),
    "so2": (0.0, 1000.0),
    "co": (0.0, 100.0),
    "o3": (0.0, 800.0),
    "no": (0.0, 1000.0),
    "nox": (0.0, 1000.0),
    "nh3": (0.0, 1000.0),
}


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Finding:
    """One validation observation."""

    check: str
    severity: Severity
    message: str
    count: int = 0


@dataclass
class ValidationReport:
    """What validation found for one series."""

    station: str
    parameter: str
    total_records: int
    findings: list[Finding] = field(default_factory=list)
    first_at: dt.datetime | None = None
    last_at: dt.datetime | None = None
    median_interval_minutes: float | None = None
    completeness_pct: float | None = None

    @property
    def ok(self) -> bool:
        """No errors. Warnings are expected in real data and do not fail a series."""
        return not any(f.severity == Severity.ERROR for f in self.findings)

    def add(self, check: str, severity: Severity, message: str, count: int = 0) -> None:
        self.findings.append(Finding(check, severity, message, count))


def validate_series(
    station: str,
    parameter: str,
    points: list[tuple[dt.datetime, float]],
) -> ValidationReport:
    """Validate one station's series for one pollutant.

    `points` is (measured_at UTC, value), in any order.
    """
    report = ValidationReport(station=station, parameter=parameter, total_records=len(points))

    if not points:
        report.add("empty", Severity.ERROR, "No records.")
        return report

    ordered = sorted(points, key=lambda p: p[0])
    stamps = [p[0] for p in ordered]
    values = [p[1] for p in ordered]
    report.first_at, report.last_at = stamps[0], stamps[-1]

    # -- duplicates ------------------------------------------------------------
    dupes = [s for s, n in Counter(stamps).items() if n > 1]
    if dupes:
        report.add(
            "duplicate_timestamps",
            Severity.WARNING,
            f"{len(dupes)} timestamps appear more than once; the uniqueness "
            "constraint will collapse these on insert.",
            len(dupes),
        )

    # -- impossible values -----------------------------------------------------
    low, high = PLAUSIBLE_RANGE.get(parameter, (0.0, float("inf")))
    below = [v for v in values if v < low]
    if below:
        report.add(
            "below_floor",
            Severity.ERROR,
            f"{len(below)} values below {low:g} for {parameter} — physically impossible "
            "(a negative mass concentration cannot exist).",
            len(below),
        )
    excessive = [v for v in values if v > high]
    if excessive:
        report.add(
            "implausible_values",
            Severity.WARNING,
            f"{len(excessive)} values above {high:g} for {parameter}; likely instrument error.",
            len(excessive),
        )

    # -- stuck sensor ----------------------------------------------------------
    # A sensor repeating one value all day is broken, but reads as valid data.
    if len(values) > 10 and len(set(values)) == 1:
        report.add(
            "constant_value",
            Severity.WARNING,
            f"Every one of {len(values)} readings is {values[0]:g} — sensor may be stuck.",
            len(values),
        )

    # -- sampling interval -----------------------------------------------------
    if len(stamps) > 1:
        gaps = [
            (b - a).total_seconds() / 60
            for a, b in itertools.pairwise(stamps)
            if (b - a).total_seconds() > 0
        ]
        if gaps:
            median = statistics.median(gaps)
            report.median_interval_minutes = round(median, 1)

            span_minutes = (stamps[-1] - stamps[0]).total_seconds() / 60
            expected = (span_minutes / median) + 1 if median > 0 else len(stamps)
            report.completeness_pct = round(min(100.0, len(stamps) / expected * 100), 1)

            # Gaps relative to the series' own cadence, not to a presumed hour.
            big = [g for g in gaps if g > median * 4]
            if big:
                report.add(
                    "sampling_gaps",
                    Severity.WARNING,
                    f"{len(big)} gaps exceed 4x the median interval "
                    f"({median:.0f} min); largest {max(big):.0f} min.",
                    len(big),
                )

            if report.completeness_pct is not None and report.completeness_pct < 50:
                report.add(
                    "low_completeness",
                    Severity.WARNING,
                    f"Only {report.completeness_pct:.0f}% of expected observations present.",
                )

    # -- outliers --------------------------------------------------------------
    # Reported, never removed: on Diwali night the outlier IS the signal.
    if len(values) >= 8:
        med = statistics.median(values)
        mad = statistics.median([abs(v - med) for v in values])
        if mad > 0:
            extreme = [v for v in values if abs(v - med) / (1.4826 * mad) > 5]
            if extreme:
                report.add(
                    "outliers",
                    Severity.INFO,
                    f"{len(extreme)} readings beyond 5 MAD of the median "
                    f"(max {max(extreme):g}). Reported, not removed — a pollution "
                    "event is an outlier by construction.",
                    len(extreme),
                )

    return report


def validate_coordinates(latitude: float, longitude: float) -> list[Finding]:
    """Check a station's coordinates are real and plausibly in the Delhi NCR."""
    findings: list[Finding] = []
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        findings.append(Finding("coordinates", Severity.ERROR, f"Invalid: {latitude},{longitude}"))
        return findings
    if latitude == 0 and longitude == 0:
        findings.append(Finding("coordinates", Severity.ERROR, "Null Island (0,0) — missing data."))
        return findings
    # Generous NCR box; outside it the station is not what we think it is.
    if not (27.5 <= latitude <= 29.5 and 76.0 <= longitude <= 78.5):
        findings.append(
            Finding("coordinates", Severity.WARNING, f"Outside Delhi NCR: {latitude},{longitude}")
        )
    return findings
