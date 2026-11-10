"""Bounded, in-memory parsing. No uploaded file is persisted or executed."""
import csv
from io import BytesIO, StringIO
from pathlib import PurePosixPath
import zipfile

from flask import Request
from openpyxl import load_workbook
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from .security import validate_amount, validate_category

REQUIRED = ("category", "estimated", "actual")
MAX_UNCOMPRESSED = 20 * 1024 * 1024


class InMemoryUploadRequest(Request):
    def _get_file_stream(
        self, total_content_length: int | None, content_type: str | None,
        filename: str | None = None, content_length: int | None = None,
    ) -> BytesIO:
        # Werkzeug otherwise spools larger uploads to disk before our parser runs.
        # Flask's 2 MB request limit bounds these in-memory file streams.
        return BytesIO()


class UploadError(ValueError):
    """An expected file-validation failure that can be shown to the user."""


def _validated_rows(records, max_rows: int) -> list[dict]:
    try:
        header = next(records)
    except StopIteration:
        raise UploadError("The file is empty.") from None
    names = [str(cell or "").strip().lower() for cell in header]
    missing = [name.title() for name in REQUIRED if name not in names]
    if missing:
        raise UploadError("Missing required columns: " + ", ".join(missing) + ".")
    if any(names.count(name) > 1 for name in REQUIRED):
        raise UploadError("Required column names must not be repeated.")
    positions = {name: names.index(name) for name in REQUIRED}
    rows, errors = [], []
    row_count = error_count = 0
    for number, record in enumerate(records, start=2):
        if not record or all(value is None or str(value).strip() == "" for value in record):
            continue
        row_count += 1
        if row_count > max_rows:
            raise UploadError(f"Use at most {max_rows:,} data rows per upload.")
        values = {name: record[index] if index < len(record) else None for name, index in positions.items()}
        row_errors = []
        result = {}
        for name in REQUIRED:
            try:
                result[name] = (validate_category("" if values[name] is None else str(values[name])) if name == "category"
                                else validate_amount(values[name]))
            except ValueError as error:
                row_errors.append(f"{name.title()}: {error}")
        if row_errors:
            error_count += 1
            if len(errors) < 10:
                errors.append(f"Row {number}: " + " ".join(row_errors))
        else:
            rows.append(result)
    if errors:
        suffix = f" Showing the first 10 of {error_count} invalid rows." if error_count > 10 else ""
        raise UploadError("No rows imported. " + " ".join(errors) + suffix)
    if not rows:
        raise UploadError("The file contains no cost data rows.")
    return rows


def parse_upload(file: FileStorage | None, max_rows: int = 1000, max_bytes: int = 2 * 1024 * 1024) -> list[dict]:
    if file is None or not file.filename:
        raise UploadError("Choose a CSV or XLSX file to upload.")
    # This name is used only for validation/display; never as a filesystem path.
    name = secure_filename(file.filename)
    extension = PurePosixPath(name).suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise UploadError("Only .csv and .xlsx files are supported.")
    data = file.stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RequestEntityTooLarge()
    if not data:
        raise UploadError("The file is empty.")
    if extension == ".csv":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise UploadError("CSV files must contain UTF-8 text.") from None
        if "\x00" in text:
            raise UploadError("CSV files must not contain binary or null bytes.")
        try:
            return _validated_rows(iter(csv.reader(StringIO(text, newline=""), strict=True)), max_rows)
        except csv.Error:
            raise UploadError("This file could not be read as a CSV spreadsheet.") from None
    if not data.startswith(b"PK\x03\x04"):
        raise UploadError("This is not a valid XLSX workbook.")
    workbook = None
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            files = archive.infolist()
            if sum(info.file_size for info in files) >= MAX_UNCOMPRESSED or len(files) > 10_000:
                raise UploadError("The expanded workbook is too large (maximum 20 MB).")
            if any(info.flag_bits & 1 for info in files):
                raise UploadError("Password-protected workbooks are not supported.")
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
        sheet = workbook.worksheets[0]
        # Untrusted dimension hints can otherwise create enormous empty iteration ranges.
        sheet.reset_dimensions()
        return _validated_rows(iter(sheet.iter_rows(values_only=True)), max_rows)
    except UploadError:
        raise
    except Exception:
        raise UploadError("This file could not be read as an XLSX workbook.") from None
    finally:
        if workbook:
            workbook.close()
