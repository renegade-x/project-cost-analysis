import pytest
from app.analysis import aggregate_by_category, compute_rows, compute_totals


@pytest.mark.parametrize("estimated,actual,variance,pct,status", [
    (100, 120, 20, 20, "over budget"), (100, 80, -20, -20, "under budget"),
    (100, 100, 0, 0, "on budget"), (0, 20, 20, None, "over budget"),
    (0, 0, 0, None, "on budget"), (3, 4, 1, 33.33, "over budget"),
    (1.005, 1.015, .01, .99, "over budget"),
])
def test_calculation_and_rounding(estimated, actual, variance, pct, status):
    row = compute_rows([dict(category="A", estimated=estimated, actual=actual)])[0]
    assert (row["variance"], row["pct_variance"], row["status"]) == (variance, pct, status)


def test_totals_repeated_categories_and_empty():
    rows = compute_rows([
        dict(category="A", estimated=100, actual=120),
        dict(category="A", estimated=50, actual=40),
        dict(category="B", estimated=50, actual=50),
    ])
    assert compute_totals(rows)["variance"] == 10
    assert compute_totals(rows)["pct_variance"] == 5
    grouped = aggregate_by_category(rows)
    assert grouped[0]["estimated"] == 150
    assert grouped[0]["variance"] == 10
    assert grouped[0]["pct_variance"] == 6.67
    assert compute_rows([]) == aggregate_by_category([]) == []
    assert compute_totals([])["pct_variance"] is None
    assert compute_totals([])["estimated"] == 0


def test_decimal_totals_do_not_drift():
    rows = compute_rows([dict(category="A", estimated=.1, actual=.2)] * 10)
    assert compute_totals(rows)["estimated"] == 1
    assert compute_totals(rows)["actual"] == 2
