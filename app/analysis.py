"""Deterministic calculations, independent of Flask and the database."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

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
