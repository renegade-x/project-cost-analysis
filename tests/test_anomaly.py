from app.analysis import compute_rows, detect_anomalies
from sample_data.make_sample_data import ROWS


def rows(pairs):
    return compute_rows([dict(category=str(index), estimated=e, actual=a) for index, (e, a) in enumerate(pairs)])


def test_obvious_outlier_among_normal_rows():
    result = detect_anomalies(rows([(100, 102)] * 10 + [(100, 190)]))
    assert len(result) == 1 and result[0]["category"] == "10"
    assert result[0]["method"] == "z-score"


def test_identical_values_do_not_divide_by_zero():
    assert detect_anomalies(rows([(100, 102)] * 10)) == []


def test_small_dataset_uses_absolute_fixed_threshold():
    result = detect_anomalies(rows([(100, 125), (100, 70), (100, 101)]))
    assert len(result) == 2
    assert all(row["method"] == "fixed threshold" and row["z_score"] is None for row in result)


def test_zero_estimate_and_empty():
    result = detect_anomalies(rows([(0, 10), (0, 0)]))
    assert len(result) == 1
    assert result[0]["reason"] == "No estimate was provided"
    assert detect_anomalies([]) == []


def test_sample_flags_exactly_emergency_repairs():
    sample = compute_rows([dict(category=name, estimated=e, actual=a) for name, e, a in ROWS])
    assert [row["category"] for row in detect_anomalies(sample)] == ["Emergency repairs"]
