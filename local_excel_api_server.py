import difflib
import importlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env_file(path: str = ".env") -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return parse_env_text(f.read())


def get_openpyxl():
    try:
        return importlib.import_module("openpyxl")
    except ModuleNotFoundError as exc:
        raise RuntimeError("openpyxl is required. Install with: pip install openpyxl") from exc


STUDENT_COLUMNS = [
    "Name",
    "Department",
    "Year",
    "Section",
    "Math",
    "Science",
    "English",
    "Programming",
    "Info",
    "Total",
    "Percentage",
]


class LocalExcelStore:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self._ensure_workbook()

    @staticmethod
    def _format_name(name: str) -> str:
        return " ".join(part.capitalize() for part in str(name).strip().split())

    @staticmethod
    def _compute_total_percentage(record: dict):
        m = int(record.get("Math", 0) or 0)
        s = int(record.get("Science", 0) or 0)
        e = int(record.get("English", 0) or 0)
        p = int(record.get("Programming", 0) or 0)
        total = m + s + e + p
        record["Total"] = total
        record["Percentage"] = round((total / 400) * 100, 2)

    def _ensure_workbook(self):
        openpyxl = get_openpyxl()
        Workbook = openpyxl.Workbook
        load_workbook = openpyxl.load_workbook

        if not os.path.exists(self.excel_path):
            wb = Workbook()
            ws = wb.active
            ws.title = "Students"
            ws.append(STUDENT_COLUMNS)
            wb.save(self.excel_path)
            return

        wb = load_workbook(self.excel_path)
        ws = wb.active
        header = [cell.value for cell in ws[1]] if ws.max_row >= 1 else []
        if header != STUDENT_COLUMNS:
            ws.delete_rows(1, ws.max_row)
            ws.append(STUDENT_COLUMNS)
            wb.save(self.excel_path)

    def _read_all(self) -> list[dict]:
        openpyxl = get_openpyxl()
        load_workbook = openpyxl.load_workbook

        self._ensure_workbook()
        wb = load_workbook(self.excel_path)
        ws = wb.active

        rows: list[dict] = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(cell is not None and str(cell).strip() != "" for cell in row):
                continue
            record = {col: row[idx] for idx, col in enumerate(STUDENT_COLUMNS)}
            rows.append(record)
        return rows

    def _write_all(self, rows: list[dict]):
        openpyxl = get_openpyxl()
        Workbook = openpyxl.Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Students"
        ws.append(STUDENT_COLUMNS)
        for row in rows:
            ws.append([row.get(col, "") for col in STUDENT_COLUMNS])
        wb.save(self.excel_path)

    def get_all_students(self) -> list[dict]:
        return self._read_all()

    def get_student_by_name(self, name: str):
        target = name.strip().lower()
        if not target:
            return None
        rows = self._read_all()
        contains = [r for r in rows if target in str(r.get("Name", "")).strip().lower()]
        if contains:
            return contains[0]
        for row in rows:
            if str(row.get("Name", "")).strip().lower() == target:
                return row
        return None

    def get_student_by_name_exact(self, name: str):
        target = name.strip().lower()
        if not target:
            return None
        for row in self._read_all():
            if str(row.get("Name", "")).strip().lower() == target:
                return row
        return None

    def suggest_student_names(self, typed_name: str, limit: int = 5) -> list[str]:
        names = [
            str(r.get("Name", "")).strip()
            for r in self._read_all()
            if r.get("Name")
        ]
        if not names:
            return []

        typed = typed_name.strip().lower()
        contains_matches = [n for n in names if typed and typed in n.lower()]
        if len(contains_matches) >= limit:
            return contains_matches[:limit]

        fuzzy_matches = difflib.get_close_matches(typed_name.strip(), names, n=limit, cutoff=0.45)
        merged: list[str] = []
        for candidate in contains_matches + fuzzy_matches:
            if candidate not in merged:
                merged.append(candidate)
        return merged[:limit]

    def add_student(self, student: dict):
        rows = self._read_all()
        record = {
            "Name": self._format_name(student["Name"]),
            "Department": str(student.get("Department", "")).strip().capitalize(),
            "Year": str(student.get("Year", "")).strip(),
            "Section": str(student.get("Section", "")).strip().upper(),
            "Math": int(student.get("Math", 0) or 0),
            "Science": int(student.get("Science", 0) or 0),
            "English": int(student.get("English", 0) or 0),
            "Programming": int(student.get("Programming", 0) or 0),
            "Info": str(student.get("Info", "")).strip(),
            "Total": 0,
            "Percentage": 0,
        }
        self._compute_total_percentage(record)
        rows.append(record)
        self._write_all(rows)
        return record

    def update_student(self, name: str, update_data: dict):
        rows = self._read_all()
        target = name.strip().lower()

        for idx, row in enumerate(rows):
            if str(row.get("Name", "")).strip().lower() == target:
                merged = {**row, **update_data}
                merged["Name"] = self._format_name(str(merged.get("Name", "")).strip())
                merged["Department"] = str(merged.get("Department", "")).strip().capitalize()
                merged["Year"] = str(merged.get("Year", "")).strip()
                merged["Section"] = str(merged.get("Section", "")).strip().upper()
                merged["Math"] = int(merged.get("Math", 0) or 0)
                merged["Science"] = int(merged.get("Science", 0) or 0)
                merged["English"] = int(merged.get("English", 0) or 0)
                merged["Programming"] = int(merged.get("Programming", 0) or 0)
                merged["Info"] = str(merged.get("Info", "")).strip()
                self._compute_total_percentage(merged)
                rows[idx] = merged
                self._write_all(rows)
                return merged

        raise RuntimeError(f"Student '{name}' not found")

    def get_student_total(self, name: str):
        student = self.get_student_by_name(name)
        if not student:
            return None
        return {
            "name": student.get("Name", name),
            "total": student.get("Total", 0),
            "percentage": student.get("Percentage", 0),
            "math": student.get("Math", 0),
            "science": student.get("Science", 0),
            "english": student.get("English", 0),
            "programming": student.get("Programming", 0),
        }


def json_response(handler: BaseHTTPRequestHandler, status: int, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler: BaseHTTPRequestHandler, status: int, message: str):
    json_response(handler, status, {"error": message})


class Handler(BaseHTTPRequestHandler):
    store: LocalExcelStore | None = None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                json_response(self, 200, {"ok": True})
                return

            if path == "/students":
                json_response(self, 200, self.store.get_all_students())
                return

            if path == "/students/search":
                name = (query.get("name") or [""])[0]
                json_response(self, 200, self.store.get_student_by_name(name))
                return

            if path == "/students/exact":
                name = (query.get("name") or [""])[0]
                json_response(self, 200, self.store.get_student_by_name_exact(name))
                return

            if path == "/students/suggest":
                name = (query.get("name") or [""])[0]
                limit = int((query.get("limit") or ["5"])[0])
                json_response(self, 200, self.store.suggest_student_names(name, limit))
                return

            if path == "/students/total":
                name = (query.get("name") or [""])[0]
                json_response(self, 200, self.store.get_student_total(name))
                return

            error_response(self, 404, "Not found")
        except Exception as exc:
            error_response(self, 500, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/students":
            error_response(self, 404, "Not found")
            return

        try:
            payload = self._read_json()
            result = self.store.add_student(payload)
            json_response(self, 201, result)
        except Exception as exc:
            error_response(self, 400, str(exc))

    def do_PATCH(self):
        parsed = urlparse(self.path)
        prefix = "/students/"
        if not parsed.path.startswith(prefix):
            error_response(self, 404, "Not found")
            return

        try:
            name = unquote(parsed.path[len(prefix):])
            payload = self._read_json()
            result = self.store.update_student(name, payload)
            json_response(self, 200, result)
        except Exception as exc:
            error_response(self, 400, str(exc))


def main():
    values = load_env_file(".env")
    host = os.getenv("LOCAL_API_HOST", values.get("LOCAL_API_HOST", "127.0.0.1"))
    port = int(os.getenv("LOCAL_API_PORT", values.get("LOCAL_API_PORT", "8001")))
    excel_path = os.getenv("LOCAL_EXCEL_PATH", values.get("LOCAL_EXCEL_PATH", "chat.xlsx"))

    Handler.store = LocalExcelStore(excel_path)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Local Excel API running at http://{host}:{port}")
    print(f"Excel file: {excel_path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
