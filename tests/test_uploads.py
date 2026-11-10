from io import BytesIO
import zipfile
import pytest
from flask import request
from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import CostItem, Project
from app.uploads import MAX_UNCOMPRESSED, UploadError, parse_upload

HEADER = b"Category,Estimated,Actual\n"


def upload(client, project_id, data, filename="costs.csv"):
    return client.post(f"/projects/{project_id}/upload", data={"file": (BytesIO(data), filename)}, follow_redirects=True)


def workbook_bytes(rows) -> bytes:
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    result = BytesIO()
    workbook.save(result)
    workbook.close()
    return result.getvalue()


@pytest.mark.parametrize("extension", ["csv", "xlsx", "CSV"])
def test_valid_import(app, client, owned_project, extension):
    data = HEADER + b"Materials,100,125\nLabour,50,45\n"
    if extension == "xlsx":
        data = workbook_bytes([["Category", "Estimated", "Actual"], ["Materials", 100, 125], ["Labour", 50, 45]])
    response = upload(client, owned_project.id, data, f"costs.{extension}")
    assert b"Imported 2 cost rows" in response.data
    with app.app_context():
        assert len(db.session.scalars(db.select(CostItem)).all()) == 2


@pytest.mark.parametrize("data,filename,message", [
    (HEADER + b"A,1,2", "costs.txt", b"Only .csv and .xlsx"),
    (b"\xff\x00binary", "fake.csv", b"UTF-8"), (b"abc\x00", "fake.csv", b"null bytes"),
    (b"not zip", "fake.xlsx", b"not a valid XLSX"),
    (b"Category,Estimated\nA,1", "costs.csv", b"Actual"),
    (HEADER + b"A,1,2\nB,abc,3", "costs.csv", b"Row 3"),
    (HEADER + b"A,-1,2", "costs.csv", b"Row 2"),
    (HEADER + b"A,NaN,2", "costs.csv", b"finite"),
    (HEADER + b"A,1,Infinity", "costs.csv", b"finite"),
    (HEADER + b"A,1,2\n" * 1001, "costs.csv", b"at most 1,000"),
    (b"", "empty.csv", b"empty"), (HEADER, "header.csv", b"no cost data"),
    (HEADER + b'"broken,1,2', "broken.csv", b"could not be read"),
    (b"Category,Estimated,Actual,actual\nA,1,2,3", "duplicate.csv", b"not be repeated"),
])
def test_invalid_upload_is_atomic(app, client, owned_project, data, filename, message):
    response = upload(client, owned_project.id, data, filename)
    assert message in response.data
    with app.app_context():
        assert db.session.scalar(db.select(CostItem)) is None


def test_missing_file_and_size(client, owned_project):
    response = client.post(f"/projects/{owned_project.id}/upload", follow_redirects=True)
    assert b"Choose a CSV" in response.data
    assert upload(client, owned_project.id, b"x" * (2 * 1024 * 1024 + 1)).status_code == 413


def test_csv_injection_and_header_normalization(app, client, owned_project):
    response = upload(client, owned_project.id, b"\xef\xbb\xbf category , estimated , ACTUAL , Extra\n=1+1,100,120,ignored\n")
    assert b"Imported 1 cost rows" in response.data
    with app.app_context():
        assert db.session.scalar(db.select(CostItem)).category == "'=1+1"


def test_zip_bomb_guard():
    data = BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("large.xml", b"0" * MAX_UNCOMPRESSED)
    file = FileStorage(stream=BytesIO(data.getvalue()), filename="bomb.xlsx")
    with pytest.raises(UploadError, match="expanded workbook"):
        parse_upload(file)


def test_errors_capped_and_xlsx_formula_rejected():
    file = FileStorage(stream=BytesIO(HEADER + b"A,wrong,2\n" * 20), filename="bad.csv")
    with pytest.raises(UploadError, match="first 10 of 20") as error:
        parse_upload(file)
    assert "Row 12:" not in str(error.value)
    formula = workbook_bytes([["Category", "Estimated", "Actual"], ["=1+1", 1, 2]])
    with pytest.raises(UploadError, match="Category is required"):
        parse_upload(FileStorage(stream=BytesIO(formula), filename="formula.xlsx"))


def test_upload_clears_summary(app, client, owned_project):
    with app.app_context():
        project = db.session.get(Project, owned_project.id)
        project.ai_summary = "Old"
        db.session.commit()
    upload(client, owned_project.id, HEADER + b"A,1,2")
    with app.app_context():
        assert db.session.get(Project, owned_project.id).ai_summary is None


def test_xlsx_zero_category_is_preserved(app, client, owned_project):
    data = workbook_bytes([["Category", "Estimated", "Actual"], [0, 1, 2]])
    response = upload(client, owned_project.id, data, "zero.xlsx")
    assert b"Imported 1 cost rows" in response.data
    with app.app_context():
        assert db.session.scalar(db.select(CostItem)).category == "0"


def test_control_only_category_is_rejected_but_literal_quote_is_valid():
    file = FileStorage(stream=BytesIO(HEADER + b"\t,1,2"), filename="control.csv")
    with pytest.raises(UploadError, match="Category is required"):
        parse_upload(file)
    quote = FileStorage(stream=BytesIO(HEADER + b"',1,2"), filename="quote.csv")
    assert parse_upload(quote)[0]["category"] == "'"


def test_multipart_uploads_remain_in_memory_above_spooling_threshold(app):
    payload = b"Category,Estimated,Actual,Ignored\n" + (b"A,1,2," + b"x" * 10000 + b"\n") * 60
    assert len(payload) > 500 * 1024
    with app.test_request_context("/projects/1/upload", method="POST", data={"file": (BytesIO(payload), "large-valid.csv")}):
        uploaded = request.files["file"]
        assert isinstance(uploaded.stream, BytesIO)
        assert len(parse_upload(uploaded)) == 60
