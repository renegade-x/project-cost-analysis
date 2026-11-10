"""Generate small safe demo inputs and adversarial validation examples."""
import csv
from pathlib import Path
from openpyxl import Workbook

DIRECTORY = Path(__file__).resolve().parent
ROWS = [
    ("Materials", 12000, 12480), ("Labour", 18000, 18360),
    ("Equipment", 6000, 6120), ("Transport", 2500, 2550),
    ("Permits", 1200, 1200), ("Site preparation", 4500, 4590),
    ("Electrical", 8000, 8160), ("Plumbing", 5500, 5610),
    ("Finishing", 7000, 7140), ("Safety", 1500, 1530),
    ("Inspection", 1800, 1836), ("Emergency repairs", 2000, 5800),
]


def write_csv(name: str, rows: list, header=("Category", "Estimated", "Actual")) -> None:
    with (DIRECTORY / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    write_csv("valid_costs.csv", ROWS)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Category", "Estimated", "Actual"])
    for row in ROWS:
        sheet.append(row)
    workbook.save(DIRECTORY / "valid_costs.xlsx")
    (DIRECTORY / "fake_upload.csv").write_bytes(b"\x00\xffNot a spreadsheet")
    write_csv("formula_injection.csv", [("=1+1", 100, 120), ("+SUM(A1:A2)", 200, 180), ("@example", 50, 50), ("-unsafe", 50, 50)])
    write_csv("xss_category.csv", [("<script>alert(1)</script>", 100, 120)])
    write_csv("missing_columns.csv", [("Materials", 100)], ("Category", "Estimated"))
    write_csv("too_large.csv", [("Oversized sample" * 6, 100, 100)] * 25000)
    print("Generated demo and validation samples in", DIRECTORY)


if __name__ == "__main__":
    main()
