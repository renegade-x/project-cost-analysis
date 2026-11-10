"""Deterministic calculations, independent of Flask and the database."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable
from statistics import mean, pstdev

_CENT = Decimal("0.01")


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _result(estimated: Decimal, actual: Decimal) -> dict:
    variance = actual - estimated
    percent = (variance / estimated * 100).quantize(_CENT, rounding=ROUND_HALF_UP) if estimated else None
    return {
        "estimated": float(estimated), "actual": float(actual),
        "variance": float(variance), "pct_variance": float(percent) if percent is not None else None,
        "status": "over budget" if variance > 0 else "under budget" if variance < 0 else "on budget",
    }


def compute_rows(items: Iterable[Any]) -> list[dict]:
    rows = []
    for item in items:
        values = item if isinstance(item, dict) else vars(item)
        rows.append({"category": values["category"], **_result(
            _decimal(values["estimated"]), _decimal(values["actual"])
        )})
    return rows


def compute_totals(rows: Iterable[dict]) -> dict:
    estimated = actual = Decimal(0)
    for row in rows:
        estimated += _decimal(row["estimated"])
        actual += _decimal(row["actual"])
    return _result(estimated, actual)


def aggregate_by_category(rows: Iterable[dict]) -> list[dict]:
    grouped = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for row in rows:
        grouped[row["category"]][0] += _decimal(row["estimated"])
        grouped[row["category"]][1] += _decimal(row["actual"])
    return [{"category": name, **_result(*values)} for name, values in grouped.items()]


def detect_anomalies(rows: list[dict], z_threshold: float = 2.0, fallback_pct: float = 25.0) -> list[dict]:
    values = [row["pct_variance"] for row in rows if row["pct_variance"] is not None]
    average = mean(values) if values else 0
    deviation = pstdev(values) if len(values) >= 5 else 0
    use_z = len(values) >= 5 and deviation > 0
    anomalies = []
    for row in rows:
        percent = row["pct_variance"]
        z_score = (percent - average) / deviation if use_z and percent is not None else None
        if row["estimated"] == 0 and row["actual"] > 0:
            reason, method = "No estimate was provided", "no estimate"
        elif percent is not None and ((use_z and abs(z_score) >= z_threshold)
                                     or (not use_z and abs(percent) >= fallback_pct)):
            direction = "above" if percent > 0 else "below"
            reason = f"Actual cost is {abs(percent):.1f}% {direction} estimate"
            reason += (", far from the typical variance of the other items."
                       if use_z else f", meeting the {fallback_pct:g}% review threshold.")
            method = "z-score" if use_z else "fixed threshold"
        else:
            continue
        anomalies.append({**row, "z_score": round(z_score, 2) if z_score is not None else None,
                          "method": method, "reason": reason})
    return anomalies
