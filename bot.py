import asyncio
import difflib
import html
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

DEFAULT_SHEETDB_API_URL = ""
SHEETDB_BASE_URL = "https://sheetdb.io/api/v1/"
SHEETDB_API_KEY_STORAGE_KEY = "studentbot-sheetdb-key"
SHEETDB_API_URL_LEGACY_STORAGE_KEY = "studentbot-sheetdb-api"

HELP_TEXT = (
    "Here's what I can help you with:\n\n"
    "Student Management\n"
    "- add a student\n"
    "- update student\n"
    "- update student <name>\n"
    "- get student <name>\n"
    "- get total <name>\n\n"
    "View Data\n"
    "- show all students\n\n"
    "Mode Control (Frontend)\n"
    "- set mode local\n"
    "- set mode local-storage\n"
    "- set mode sheetdb\n"
    "- set sheetdb api <api_id_or_url>\n"
    "- reload env\n"
    "- current mode\n\n"
    "Local Storage Tools\n"
    "- local storage status\n"
    "- clear local storage\n\n"
    "Chat\n"
    "- hi / hello / hey\n"
    "- tell me a fact\n"
    "- help\n\n"
    "Notes\n"
    "- First load can take longer because Python runs in the browser.\n"
    "- On hosted pages, local mode is disabled; use sheetdb mode."
)


def _read_lines(path: str, fallback: list[str]) -> list[str]:
    if not os.path.exists(path):
        return fallback
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines or fallback


GREETINGS = _read_lines(
    "greetings.txt",
    [
        "Hi there!",
        "Hello!",
        "Hey! Ready to help.",
    ],
)

FACTS = _read_lines(
    "facts.txt",
    [
        "The first email was sent in 1971.",
        "Honey can stay edible for thousands of years.",
    ],
)


def _parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _is_valid_sheetdb_url(value: str) -> bool:
    url = value.strip()
    return bool(url) and "YOUR_API_ID" not in url


def _normalize_sheetdb_url(value: str) -> str:
    candidate = value.strip().strip("/")
    if not candidate or "YOUR_API_ID" in candidate:
        return ""

    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate

    if all(ch.isalnum() or ch in "-_" for ch in candidate):
        return f"{SHEETDB_BASE_URL}{candidate}"

    return ""


def _extract_sheetdb_key(value: str) -> str:
    normalized = _normalize_sheetdb_url(value)
    if not normalized:
        return ""
    marker = "/api/v1/"
    if marker in normalized:
        return normalized.split(marker, 1)[1].strip().strip("/")
    return ""


async def _fetch_with_timeout(coro, timeout_seconds: float, timeout_message: str):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(timeout_message) from exc


def _load_local_env_file(path: str = ".env") -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return _parse_env_text(f.read())


@dataclass
class RuntimeConfig:
    sheetdb_api_url: str = ""
    local_excel_path: str = "chat.xlsx"
    local_api_url: str = "http://127.0.0.1:8001"
    data_mode: str = "local"
    browser_host: str = ""
    browser_is_localhost: bool = True
    mode_notice: str = ""

    def configured(self) -> bool:
        return self.data_mode in {"local", "local-storage"} or bool(self.sheetdb_api_url)

    def using_sheetdb(self) -> bool:
        return self.data_mode == "sheetdb"

    def using_local(self) -> bool:
        return self.data_mode == "local"

    @staticmethod
    def _normalize_mode(value: str) -> str:
        mode = value.strip().lower()
        return mode if mode in {"sheetdb", "local", "local-storage"} else "sheetdb"

    async def load_browser_env(self):
        self.mode_notice = ""

        try:
            from js import window  # type: ignore

            self.browser_host = str(window.location.hostname)
            self.browser_is_localhost = self.browser_host in {"localhost", "127.0.0.1", "::1"}
        except Exception:
            self.browser_host = ""
            self.browser_is_localhost = True

        # Browser mode: environment variables are usually empty in Pyodide.
        # Avoid fetching .env from browser to prevent 404s on static hosting.
        env_mode = os.getenv("DATA_MODE", "").strip()
        self.sheetdb_api_url = os.getenv("SHEETDB_API_URL", "").strip()
        self.local_excel_path = os.getenv("LOCAL_EXCEL_PATH", "chat.xlsx").strip() or "chat.xlsx"
        self.local_api_url = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8001").strip() or "http://127.0.0.1:8001"
        self.data_mode = self._normalize_mode(env_mode or "local")

        # On hosted pages, restore SheetDB configuration from local storage
        # so users don't need to re-enter the API key on every refresh.
        if not self.browser_is_localhost:
            try:
                from js import localStorage  # type: ignore

                saved_key = str(localStorage.getItem(SHEETDB_API_KEY_STORAGE_KEY) or "").strip()
                saved_url = str(localStorage.getItem(SHEETDB_API_URL_LEGACY_STORAGE_KEY) or "").strip()
                persisted = _normalize_sheetdb_url(saved_key) or _normalize_sheetdb_url(saved_url)
                if persisted:
                    self.sheetdb_api_url = persisted
            except Exception:
                pass

        requested_mode = self.data_mode
        if not self.browser_is_localhost:
            if requested_mode == "local":
                if _is_valid_sheetdb_url(self.sheetdb_api_url):
                    self.data_mode = "sheetdb"
                    self.mode_notice = (
                        "Local mode is only available on localhost. "
                        "Switched to sheetdb mode for hosted frontend."
                    )
                else:
                    self.data_mode = "local-storage"
                    self.mode_notice = (
                        "Local mode is only available on localhost and SheetDB is not configured. "
                        "Switched to local-storage mode."
                    )
            elif requested_mode == "sheetdb" and not _is_valid_sheetdb_url(self.sheetdb_api_url):
                self.data_mode = "local-storage"
                self.mode_notice = (
                    "SHEETDB_API_URL is missing/invalid in hosted mode. "
                    "Switched to local-storage mode."
                )
            else:
                self.data_mode = requested_mode
        elif self.data_mode == "sheetdb" and not _is_valid_sheetdb_url(self.sheetdb_api_url):
            self.data_mode = "local"
            self.mode_notice = (
                "SHEETDB_API_URL is missing/invalid on localhost. "
                "Using local mode."
            )

    def load_cli_env(self):
        values = _load_local_env_file()

        self.sheetdb_api_url = (
            os.getenv("SHEETDB_API_URL")
            or values.get("SHEETDB_API_URL", "")
        ).strip()

        self.local_excel_path = (
            os.getenv("LOCAL_EXCEL_PATH")
            or values.get("LOCAL_EXCEL_PATH", "chat.xlsx")
            or "chat.xlsx"
        ).strip()

        self.local_api_url = (
            os.getenv("LOCAL_API_URL")
            or values.get("LOCAL_API_URL", "http://127.0.0.1:8001")
            or "http://127.0.0.1:8001"
        ).strip()

        self.data_mode = self._normalize_mode(
            os.getenv("DATA_MODE", values.get("DATA_MODE", "local"))
        )


RUNTIME_CONFIG = RuntimeConfig(
    sheetdb_api_url=DEFAULT_SHEETDB_API_URL,
    local_excel_path="chat.xlsx",
    local_api_url="http://127.0.0.1:8001",
    data_mode="local",
)


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


class LocalExcelAPI:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self._ensure_workbook()

    def _ensure_workbook(self):
        import importlib

        try:
            openpyxl = importlib.import_module("openpyxl")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "openpyxl is required for local Excel mode. Install with: pip install openpyxl"
            ) from exc

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
        import importlib

        try:
            openpyxl = importlib.import_module("openpyxl")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "openpyxl is required for local Excel mode. Install with: pip install openpyxl"
            ) from exc

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
        import importlib

        try:
            openpyxl = importlib.import_module("openpyxl")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "openpyxl is required for local Excel mode. Install with: pip install openpyxl"
            ) from exc

        Workbook = openpyxl.Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Students"
        ws.append(STUDENT_COLUMNS)
        for row in rows:
            ws.append([row.get(col, "") for col in STUDENT_COLUMNS])
        wb.save(self.excel_path)

    @staticmethod
    def _format_name(name: str) -> str:
        return " ".join(part.capitalize() for part in name.strip().split())

    @staticmethod
    def _compute_total_percentage(record: dict):
        m = int(record.get("Math", 0) or 0)
        s = int(record.get("Science", 0) or 0)
        e = int(record.get("English", 0) or 0)
        p = int(record.get("Programming", 0) or 0)
        total = m + s + e + p
        record["Total"] = total
        record["Percentage"] = round((total / 400) * 100, 2)

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
        rows = self._read_all()
        names = [str(r.get("Name", "")).strip() for r in rows if r.get("Name")]
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


class StudentSheetAPI:
    @staticmethod
    def _format_name(name: str) -> str:
        return " ".join(part.capitalize() for part in name.strip().split())

    @staticmethod
    async def _fetch_json(url: str, method: str = "GET", payload: dict | None = None):
        from js import fetch  # type: ignore
        from pyodide.ffi import to_js  # type: ignore

        options = {
            "method": method,
            "headers": {"Content-Type": "application/json"},
        }
        if payload is not None:
            options["body"] = json.dumps(payload)

        response = await _fetch_with_timeout(
            fetch(url, to_js(options)),
            8.0,
            "Request timed out while contacting SheetDB.",
        )
        if not response.ok:
            raise RuntimeError(f"HTTP error {response.status}")

        text = await _fetch_with_timeout(
            response.text(),
            8.0,
            "Timed out while reading SheetDB response.",
        )
        return json.loads(text) if text else None

    @classmethod
    async def get_all_students(cls):
        if not RUNTIME_CONFIG.configured():
            raise RuntimeError("SHEETDB_API_URL is not configured")
        return await cls._fetch_json(RUNTIME_CONFIG.sheetdb_api_url)

    @classmethod
    async def get_student_by_name(cls, name: str):
        if not RUNTIME_CONFIG.configured():
            raise RuntimeError("SHEETDB_API_URL is not configured")
        search_url = (
            f"{RUNTIME_CONFIG.sheetdb_api_url}/search?Name=*{quote(name)}*&casesensitive=false"
        )
        data = await cls._fetch_json(search_url)
        return data[0] if data else None

    @classmethod
    async def get_student_by_name_exact(cls, name: str):
        # SheetDB exact key lookup is case-sensitive, so we fetch and compare case-insensitively.
        students = await cls.get_all_students()
        target = name.strip().lower()
        for student in students or []:
            student_name = str(student.get("Name", "")).strip().lower()
            if student_name == target:
                return student
        return None

    @classmethod
    async def suggest_student_names(cls, typed_name: str, limit: int = 5) -> list[str]:
        students = await cls.get_all_students()
        names = [str(s.get("Name", "")).strip() for s in (students or []) if s.get("Name")]
        if not names:
            return []

        typed = typed_name.strip().lower()
        # Prioritize substring matches, then fall back to fuzzy sequence matching.
        contains_matches = [n for n in names if typed and typed in n.lower()]
        if len(contains_matches) >= limit:
            return contains_matches[:limit]

        fuzzy_matches = difflib.get_close_matches(
            typed_name.strip(), names, n=limit, cutoff=0.45
        )

        merged: list[str] = []
        for candidate in contains_matches + fuzzy_matches:
            if candidate not in merged:
                merged.append(candidate)
        return merged[:limit]

    @classmethod
    async def add_student(cls, student: dict):
        if not RUNTIME_CONFIG.configured():
            raise RuntimeError("SHEETDB_API_URL is not configured")
        math = int(student["Math"])
        science = int(student["Science"])
        english = int(student["English"])
        programming = int(student["Programming"])

        total = math + science + english + programming
        percentage = round((total / 400) * 100, 2)

        payload = {
            "data": [
                {
                    "Name": cls._format_name(student["Name"]),
                    "Department": student["Department"].strip().capitalize(),
                    "Year": str(student["Year"]).strip(),
                    "Section": student["Section"].strip().upper(),
                    "Math": math,
                    "Science": science,
                    "English": english,
                    "Programming": programming,
                    "Info": student.get("Info", "").strip(),
                    "Total": total,
                    "Percentage": percentage,
                }
            ]
        }
        return await cls._fetch_json(
            RUNTIME_CONFIG.sheetdb_api_url, method="POST", payload=payload
        )

    @classmethod
    async def update_student(cls, name: str, update_data: dict):
        if not RUNTIME_CONFIG.configured():
            raise RuntimeError("SHEETDB_API_URL is not configured")

        current = await cls.get_student_by_name_exact(name)
        if not current:
            raise RuntimeError(f"Student '{name}' not found")

        merged = {**current, **update_data}
        m = int(merged.get("Math", 0) or 0)
        s = int(merged.get("Science", 0) or 0)
        e = int(merged.get("English", 0) or 0)
        p = int(merged.get("Programming", 0) or 0)
        total = m + s + e + p
        merged["Total"] = total
        merged["Percentage"] = round((total / 400) * 100, 2)

        update_url = (
            f"{RUNTIME_CONFIG.sheetdb_api_url}/Name/{quote(str(current.get('Name', name)))}"
        )
        return await cls._fetch_json(update_url, method="PATCH", payload={"data": merged})

    @classmethod
    async def get_student_total(cls, name: str):
        student = await cls.get_student_by_name(name)
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


class BrowserLocalStoreAPI:
    @staticmethod
    def _base_url() -> str:
        return RUNTIME_CONFIG.local_api_url.rstrip("/")

    @staticmethod
    async def _fetch_json(path: str, method: str = "GET", payload: dict | None = None):
        from js import fetch  # type: ignore
        from pyodide.ffi import to_js  # type: ignore

        options = {
            "method": method,
            "headers": {"Content-Type": "application/json"},
        }
        if payload is not None:
            options["body"] = json.dumps(payload)

        try:
            response = await _fetch_with_timeout(
                fetch(f"{BrowserLocalStoreAPI._base_url()}{path}", to_js(options)),
                5.0,
                "Local API request timed out.",
            )
        except Exception as exc:
            raise RuntimeError(
                "Local API is unreachable. Start local_excel_api_server.py and verify LOCAL_API_URL in .env"
            ) from exc
        if not response.ok:
            text = await _fetch_with_timeout(
                response.text(),
                3.0,
                "Timed out while reading Local API error response.",
            )
            raise RuntimeError(text or f"HTTP error {response.status}")
        text = await _fetch_with_timeout(
            response.text(),
            5.0,
            "Timed out while reading Local API response.",
        )
        return json.loads(text) if text else None

    @classmethod
    async def get_all_students(cls):
        return await cls._fetch_json("/students")

    @classmethod
    async def get_student_by_name(cls, name: str):
        return await cls._fetch_json(f"/students/search?name={quote(name)}")

    @classmethod
    async def get_student_by_name_exact(cls, name: str):
        return await cls._fetch_json(f"/students/exact?name={quote(name)}")

    @classmethod
    async def suggest_student_names(cls, typed_name: str, limit: int = 5) -> list[str]:
        data = await cls._fetch_json(
            f"/students/suggest?name={quote(typed_name)}&limit={int(limit)}"
        )
        return data or []

    @classmethod
    async def add_student(cls, student: dict):
        return await cls._fetch_json("/students", method="POST", payload=student)

    @classmethod
    async def update_student(cls, name: str, update_data: dict):
        return await cls._fetch_json(
            f"/students/{quote(name)}", method="PATCH", payload=update_data
        )

    @classmethod
    async def get_student_total(cls, name: str):
        return await cls._fetch_json(f"/students/total?name={quote(name)}")


class BrowserMemoryStoreAPI:
    STORAGE_KEY = "studentbot-local-students-v1"

    @staticmethod
    def _format_name(name: str) -> str:
        return " ".join(part.capitalize() for part in name.strip().split())

    @classmethod
    def _read_all_sync(cls) -> list[dict]:
        from js import JSON, localStorage  # type: ignore

        raw = localStorage.getItem(cls.STORAGE_KEY)
        if not raw:
            return []
        try:
            parsed = JSON.parse(raw)
            return json.loads(JSON.stringify(parsed))
        except Exception:
            return []

    @classmethod
    def _write_all_sync(cls, rows: list[dict]):
        from js import JSON, localStorage  # type: ignore

        localStorage.setItem(cls.STORAGE_KEY, JSON.stringify(rows))

    @classmethod
    def _compute_total_percentage(cls, row: dict):
        m = int(row.get("Math", 0) or 0)
        s = int(row.get("Science", 0) or 0)
        e = int(row.get("English", 0) or 0)
        p = int(row.get("Programming", 0) or 0)
        total = m + s + e + p
        row["Total"] = total
        row["Percentage"] = round((total / 400) * 100, 2)

    @classmethod
    async def get_all_students(cls):
        return cls._read_all_sync()

    @classmethod
    async def get_student_by_name(cls, name: str):
        target = name.strip().lower()
        if not target:
            return None
        rows = cls._read_all_sync()
        contains = [r for r in rows if target in str(r.get("Name", "")).strip().lower()]
        if contains:
            return contains[0]
        for row in rows:
            if str(row.get("Name", "")).strip().lower() == target:
                return row
        return None

    @classmethod
    async def get_student_by_name_exact(cls, name: str):
        target = name.strip().lower()
        if not target:
            return None
        for row in cls._read_all_sync():
            if str(row.get("Name", "")).strip().lower() == target:
                return row
        return None

    @classmethod
    async def suggest_student_names(cls, typed_name: str, limit: int = 5) -> list[str]:
        names = [
            str(r.get("Name", "")).strip()
            for r in cls._read_all_sync()
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

    @classmethod
    async def add_student(cls, student: dict):
        rows = cls._read_all_sync()
        record = {
            "Name": cls._format_name(student["Name"]),
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
        cls._compute_total_percentage(record)
        rows.append(record)
        cls._write_all_sync(rows)
        return record

    @classmethod
    async def update_student(cls, name: str, update_data: dict):
        rows = cls._read_all_sync()
        target = name.strip().lower()
        for idx, row in enumerate(rows):
            if str(row.get("Name", "")).strip().lower() == target:
                merged = {**row, **update_data}
                merged["Name"] = cls._format_name(str(merged.get("Name", "")).strip())
                merged["Department"] = str(merged.get("Department", "")).strip().capitalize()
                merged["Year"] = str(merged.get("Year", "")).strip()
                merged["Section"] = str(merged.get("Section", "")).strip().upper()
                merged["Math"] = int(merged.get("Math", 0) or 0)
                merged["Science"] = int(merged.get("Science", 0) or 0)
                merged["English"] = int(merged.get("English", 0) or 0)
                merged["Programming"] = int(merged.get("Programming", 0) or 0)
                merged["Info"] = str(merged.get("Info", "")).strip()
                cls._compute_total_percentage(merged)
                rows[idx] = merged
                cls._write_all_sync(rows)
                return merged
        raise RuntimeError(f"Student '{name}' not found")

    @classmethod
    async def get_student_total(cls, name: str):
        student = await cls.get_student_by_name(name)
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

    @classmethod
    async def get_storage_stats(cls):
        rows = cls._read_all_sync()
        return {
            "count": len(rows),
            "names": [str(r.get("Name", "")).strip() for r in rows if r.get("Name")],
        }

    @classmethod
    async def clear_storage(cls):
        cls._write_all_sync([])
        return {"cleared": True}


class BrowserChatApp:
    def __init__(self):
        from pyscript import document  # type: ignore

        self.document = document
        self.chat_messages = document.getElementById("chatMessages")
        self.user_input = document.getElementById("userInput")
        self.send_btn = document.getElementById("sendBtn")
        self.help_btn = document.getElementById("helpBtn")
        self.typing_indicator = document.getElementById("typingIndicator")
        self.theme_toggle = document.getElementById("themeToggle")
        self.student_form_modal = document.getElementById("studentFormModal")
        self.student_form = document.getElementById("studentForm")
        self.modal_close = document.getElementById("modalClose")
        self.cancel_form = document.getElementById("cancelForm")
        self.toast_container = document.getElementById("toastContainer")

        self.conversation_state = None
        self.pending_student = {}
        self.form_mode = "add"
        self.update_target_name = ""
        self._proxies = []
        self.api = None
        self._bind_api_for_mode()

    def _bind_api_for_mode(self):
        if RUNTIME_CONFIG.data_mode == "sheetdb":
            self.api = StudentSheetAPI
        elif RUNTIME_CONFIG.data_mode == "local-storage":
            self.api = BrowserMemoryStoreAPI
        else:
            self.api = BrowserLocalStoreAPI

    def _set_frontend_mode_sync(self, mode: str, announce: bool = True, persist: bool = True) -> bool:
        target = RuntimeConfig._normalize_mode(mode)

        if target == "local" and not RUNTIME_CONFIG.browser_is_localhost:
            if announce:
                self.add_message(
                    "bot",
                    "Local mode is only available on localhost. On GitHub Pages, use sheetdb mode.",
                )
            return False

        if target == "sheetdb" and not _is_valid_sheetdb_url(RUNTIME_CONFIG.sheetdb_api_url):
            if announce:
                self.add_message(
                    "bot",
                    "Cannot switch to sheetdb mode because SHEETDB_API_URL is missing or invalid in .env. "
                    "Type: set sheetdb api YOUR_API_ID (or full URL) or use set mode local-storage",
                )
            return False

        RUNTIME_CONFIG.data_mode = target
        self._bind_api_for_mode()

        if persist:
            try:
                from js import localStorage  # type: ignore

                localStorage.setItem("studentbot-data-mode", target)
            except Exception:
                pass

        if announce:
            if target == "local-storage":
                self.add_message(
                    "bot",
                    "Switched mode to local-storage. Data is saved in this browser only.",
                )
            else:
                self.add_message("bot", f"Switched mode to {target}.")
        return True

    async def _set_frontend_mode(self, mode: str, announce: bool = True, persist: bool = True) -> bool:
        target = RuntimeConfig._normalize_mode(mode)

        if target == "sheetdb" and not _is_valid_sheetdb_url(RUNTIME_CONFIG.sheetdb_api_url):
            # Try a fresh config reload before failing mode switch.
            await RUNTIME_CONFIG.load_browser_env()

        return self._set_frontend_mode_sync(target, announce=announce, persist=persist)

    def _load_saved_frontend_mode(self):
        try:
            from js import localStorage  # type: ignore

            saved_key = str(localStorage.getItem(SHEETDB_API_KEY_STORAGE_KEY) or "").strip()
            saved_api = str(localStorage.getItem(SHEETDB_API_URL_LEGACY_STORAGE_KEY) or "").strip()
            persisted = _normalize_sheetdb_url(saved_key) or _normalize_sheetdb_url(saved_api)
            if persisted and _is_valid_sheetdb_url(persisted):
                RUNTIME_CONFIG.sheetdb_api_url = persisted

            saved_mode = localStorage.getItem("studentbot-data-mode")
            if saved_mode:
                self._set_frontend_mode_sync(str(saved_mode), announce=False, persist=False)

            # In hosted mode with no saved preference, prefer local-storage over broken sheetdb.
            if (
                not saved_mode
                and not RUNTIME_CONFIG.browser_is_localhost
                and RUNTIME_CONFIG.data_mode == "sheetdb"
                and not _is_valid_sheetdb_url(RUNTIME_CONFIG.sheetdb_api_url)
            ):
                self._set_frontend_mode_sync("local-storage", announce=False, persist=True)
        except Exception:
            pass

    def _keep_proxy(self, proxy):
        self._proxies.append(proxy)
        return proxy

    def _now(self) -> str:
        return datetime.now().strftime("%I:%M %p")

    def _safe(self, text: str) -> str:
        return html.escape(str(text)).replace("\n", "<br>")

    def add_message(self, sender: str, text: str):
        bubble = (
            f'<div class="message {sender}">'
            f'  <div class="message-avatar">{"🤖" if sender == "bot" else "👤"}</div>'
            f'  <div class="message-content">'
            f'    <div class="message-text">{self._safe(text)}</div>'
            f'    <div class="message-time">{self._now()}</div>'
            f"  </div>"
            f"</div>"
        )
        self.chat_messages.insertAdjacentHTML("beforeend", bubble)
        self.chat_messages.scrollTop = self.chat_messages.scrollHeight

    def add_html_block(self, html_block: str):
        self.chat_messages.insertAdjacentHTML("beforeend", html_block)
        self.chat_messages.scrollTop = self.chat_messages.scrollHeight

    def toast(self, message: str, toast_type: str = "info"):
        if not self.toast_container:
            return
        icon = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }.get(toast_type, "ℹ️")
        toast_html = (
            f'<div class="toast {toast_type}">'
            f'  <span class="toast-icon">{icon}</span>'
            f'  <span class="toast-message">{self._safe(message)}</span>'
            '  <button class="toast-close">&times;</button>'
            "</div>"
        )
        self.toast_container.insertAdjacentHTML("beforeend", toast_html)
        toast_el = self.toast_container.lastElementChild

        from pyodide.ffi import create_proxy  # type: ignore

        close_proxy = self._keep_proxy(create_proxy(lambda _e: toast_el.remove()))
        toast_el.querySelector(".toast-close").addEventListener("click", close_proxy)

        async def _remove_later():
            await asyncio.sleep(4)
            if toast_el and toast_el.parentElement:
                toast_el.classList.add("removing")
                await asyncio.sleep(0.3)
                if toast_el and toast_el.parentElement:
                    toast_el.remove()

        asyncio.create_task(_remove_later())

    def _theme_set(self, theme: str):
        from js import localStorage  # type: ignore

        self.document.documentElement.setAttribute("data-theme", theme)
        localStorage.setItem("studentbot-theme", theme)

    def _theme_get(self) -> str:
        return self.document.documentElement.getAttribute("data-theme") or "dark"

    def init_theme(self):
        from js import localStorage, window  # type: ignore

        saved = localStorage.getItem("studentbot-theme")
        prefers_dark = window.matchMedia("(prefers-color-scheme: dark)").matches
        self._theme_set(saved if saved else ("dark" if prefers_dark else "light"))

    def toggle_theme(self):
        next_theme = "light" if self._theme_get() == "dark" else "dark"
        self._theme_set(next_theme)
        self.toast(f"Switched to {next_theme} mode", "info")

    def open_modal(self, mode: str = "add"):
        self.form_mode = mode
        self.student_form_modal.classList.add("active")
        self.document.getElementById("modalTitle").textContent = (
            "Add New Student" if mode == "add" else "Update Student"
        )
        submit_text = self.student_form.querySelector(".btn-text")
        submit_text.textContent = "Save Student" if mode == "add" else "Update Student"
        if mode == "add":
            self.student_form.reset()
            self.update_target_name = ""
        self.document.getElementById("studentName").focus()

    def close_modal(self):
        self.student_form_modal.classList.remove("active")
        self.student_form.reset()
        self.form_mode = "add"
        self.update_target_name = ""

    async def preload_student_for_update(self, name: str):
        student = await self.api.get_student_by_name_exact(name)
        if not student:
            suggestions = await self.api.suggest_student_names(name)
            if suggestions:
                suggested_text = "\n".join(f"- {item}" for item in suggestions)
                self.add_message(
                    "bot",
                    f"No exact student name match found for: {name}.\n"
                    "Try one of these names:\n"
                    f"{suggested_text}",
                )
            else:
                self.add_message(
                    "bot",
                    f"No exact student name match found for: {name}. Please enter the full name.",
                )
            return

        self.update_target_name = student.get("Name", name)
        self.open_modal("update")
        self.document.getElementById("studentName").value = student.get("Name", "")
        self.document.getElementById("studentDept").value = student.get("Department", "")
        self.document.getElementById("studentYear").value = str(student.get("Year", ""))
        self.document.getElementById("studentSection").value = student.get("Section", "")
        self.document.getElementById("marksMath").value = str(student.get("Math", ""))
        self.document.getElementById("marksScience").value = str(student.get("Science", ""))
        self.document.getElementById("marksEnglish").value = str(student.get("English", ""))
        self.document.getElementById("marksProgramming").value = str(student.get("Programming", ""))
        self.document.getElementById("studentInfo").value = student.get("Info", "")

    def show_typing(self, visible: bool):
        if visible:
            self.typing_indicator.classList.add("active")
        else:
            self.typing_indicator.classList.remove("active")

    async def handle_send(self):
        message = self.user_input.value.strip()
        if not message:
            return
        self.user_input.value = ""
        self.add_message("user", message)

        self.show_typing(True)
        await asyncio.sleep(0.35)
        await self.process_message(message)
        self.show_typing(False)

    async def process_message(self, message: str):
        text = message.strip()
        lower = text.lower()

        if self.conversation_state in {"awaiting_search_name", "awaiting_total_name", "awaiting_update_name"}:
            await self.handle_conversation_flow(text)
            return

        if self.conversation_state:
            await self._continue_add_flow(text)
            return

        if lower in {"help", "?"}:
            self.add_message("bot", HELP_TEXT)
            return

        if lower in {"current mode", "show mode", "mode"}:
            self.add_message("bot", f"Active mode: {RUNTIME_CONFIG.data_mode}")
            return

        if lower in {"local storage status", "local-storage status", "storage status"}:
            stats = await BrowserMemoryStoreAPI.get_storage_stats()
            self.add_message(
                "bot",
                f"Local-storage records: {stats['count']}. "
                "This data stays in your current browser.",
            )
            return

        if lower in {"clear local storage", "clear local-storage", "clear storage"}:
            await BrowserMemoryStoreAPI.clear_storage()
            self.add_message("bot", "Local-storage data cleared successfully.")
            return

        if lower.startswith("set sheetdb api"):
            candidate = text[len("set sheetdb api") :].strip()
            normalized = _normalize_sheetdb_url(candidate)
            if not _is_valid_sheetdb_url(normalized):
                self.add_message(
                    "bot",
                    "Invalid SheetDB API value. Use: set sheetdb api YOUR_API_ID (or full URL).",
                )
                return
            RUNTIME_CONFIG.sheetdb_api_url = normalized
            try:
                from js import localStorage  # type: ignore

                api_key = _extract_sheetdb_key(normalized)
                if api_key:
                    localStorage.setItem(SHEETDB_API_KEY_STORAGE_KEY, api_key)
                localStorage.setItem(SHEETDB_API_URL_LEGACY_STORAGE_KEY, normalized)
            except Exception:
                pass
            await self._set_frontend_mode("sheetdb")
            return

        if lower in {"reload env", "refresh env"}:
            await RUNTIME_CONFIG.load_browser_env()
            self._bind_api_for_mode()
            self.add_message("bot", f"Environment reloaded. Active mode: {RUNTIME_CONFIG.data_mode}")
            return

        if lower.startswith("set mode"):
            target = lower[len("set mode") :].strip()
            if not target:
                self.add_message("bot", "Usage: set mode local OR set mode sheetdb")
                return
            await self._set_frontend_mode(target)
            return

        if lower in {"hi", "hello", "hey"}:
            self.add_message("bot", random.choice(GREETINGS))
            return

        if "fact" in lower or "joke" in lower:
            self.add_message("bot", random.choice(FACTS))
            return

        if lower.startswith("add a student") or lower == "add student":
            self.add_message("bot", "I'll open the form for adding a student.")
            self.open_modal("add")
            return

        if lower.startswith("update student"):
            name = text[len("update student") :].strip()
            if name:
                await self.preload_student_for_update(name)
                return
            self.conversation_state = "awaiting_update_name"
            self.add_message("bot", "Enter the exact student's name to update:")
            return

        if lower.startswith("get student"):
            name = text[len("get student") :].strip()
            if not name:
                self.conversation_state = "awaiting_search_name"
                self.add_message("bot", "What's the student's name you're looking for?")
                return
            await self._get_student(name)
            return

        if lower.startswith("get total"):
            name = text[len("get total") :].strip()
            if not name:
                self.conversation_state = "awaiting_total_name"
                self.add_message("bot", "Whose total marks would you like to see?")
                return
            await self._get_total(name)
            return

        if "show all" in lower or "all students" in lower:
            await self._show_all()
            return

        self.add_message("bot", "I did not understand that. Type help to see commands.")

    async def handle_conversation_flow(self, message: str):
        state = self.conversation_state
        self.conversation_state = None

        if state == "awaiting_search_name":
            await self._get_student(message.strip())
            return
        if state == "awaiting_total_name":
            await self._get_total(message.strip())
            return
        if state == "awaiting_update_name":
            await self.preload_student_for_update(message.strip())
            return

        self.add_message("bot", "Let's start fresh. How can I help you?")

    async def _continue_add_flow(self, message: str):
        state_order = [
            ("add_name", "Name", "Enter Department:"),
            ("add_department", "Department", "Enter Year:"),
            ("add_year", "Year", "Enter Section:"),
            ("add_section", "Section", "Enter Math marks (0-100):"),
            ("add_math", "Math", "Enter Science marks (0-100):"),
            ("add_science", "Science", "Enter English marks (0-100):"),
            ("add_english", "English", "Enter Programming marks (0-100):"),
            ("add_programming", "Programming", "Enter Additional Info (or '-' for none):"),
        ]

        current = next((x for x in state_order if x[0] == self.conversation_state), None)

        if current:
            _, field, next_prompt = current
            value = message.strip()
            if field in {"Math", "Science", "English", "Programming"}:
                if not value.isdigit() or not (0 <= int(value) <= 100):
                    self.add_message("bot", f"Please enter a valid number from 0 to 100 for {field}.")
                    return
            self.pending_student[field] = value

            next_state_index = state_order.index(current) + 1
            if next_state_index < len(state_order):
                self.conversation_state = state_order[next_state_index][0]
                self.add_message("bot", next_prompt)
                return

            self.conversation_state = "add_info"
            self.add_message("bot", "Enter Additional Info (or '-' for none):")
            return

        if self.conversation_state == "add_info":
            self.pending_student["Info"] = "" if message.strip() == "-" else message.strip()

            try:
                await self.api.add_student(self.pending_student)
                self.add_message(
                    "bot",
                    f"Student {self.pending_student['Name']} saved successfully.",
                )
            except Exception as exc:
                self.add_message("bot", f"Could not save student. Error: {exc}")

            self.conversation_state = None
            self.pending_student = {}

    async def _get_student(self, name: str):
        try:
            student = await self.api.get_student_by_name(name)
            if not student:
                self.add_message("bot", f"No student found with name: {name}")
                return

            rows = "".join(
                f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
                for k, v in student.items()
            )
            card = (
                '<div class="message bot">'
                '  <div class="message-avatar">📋</div>'
                '  <div class="message-content">'
                f'    <div class="message-text">Record for {self._safe(student.get("Name", name))}</div>'
                '    <div class="data-table-wrapper">'
                '      <table class="data-table">'
                "        <tr><th>Field</th><th>Value</th></tr>"
                f"        {rows}"
                "      </table>"
                "    </div>"
                f'    <div class="message-time">{self._now()}</div>'
                "  </div>"
                "</div>"
            )
            self.add_html_block(card)
        except Exception as exc:
            self.add_message("bot", f"Failed to fetch student data. Error: {exc}")

    async def _get_total(self, name: str):
        try:
            result = await self.api.get_student_total(name)
            if not result:
                self.add_message("bot", f"No student found with name: {name}")
                return

            total = result.get("total", 0)
            percentage = result.get("percentage", 0)
            self.add_message(
                "bot",
                f"Marks summary for {result.get('name', name)}\n"
                f"Total: {total}/400\n"
                f"Percentage: {percentage}%",
            )
        except Exception as exc:
            self.add_message("bot", f"Failed to fetch total. Error: {exc}")

    async def _show_all(self):
        try:
            students = await self.api.get_all_students()
            if not students:
                self.add_message("bot", "No students found in your sheet.")
                return

            rows = "".join(
                "<tr>"
                f"<td>{html.escape(str(s.get('Name', '')))}</td>"
                f"<td>{html.escape(str(s.get('Department', '')))}</td>"
                f"<td>{html.escape(str(s.get('Year', '')))}</td>"
                f"<td>{html.escape(str(s.get('Section', '')))}</td>"
                f"<td>{html.escape(str(s.get('Total', '')))}</td>"
                f"<td>{html.escape(str(s.get('Percentage', '')))}%</td>"
                "</tr>"
                for s in students
            )

            block = (
                '<div class="message bot">'
                '  <div class="message-avatar">📚</div>'
                '  <div class="message-content" style="max-width:100%; overflow-x:auto;">'
                f'    <div class="message-text">Total students: {len(students)}</div>'
                '    <div class="data-table-wrapper">'
                '      <table class="data-table">'
                "        <tr><th>Name</th><th>Department</th><th>Year</th><th>Section</th><th>Total</th><th>Percentage</th></tr>"
                f"        {rows}"
                "      </table>"
                "    </div>"
                f'    <div class="message-time">{self._now()}</div>'
                "  </div>"
                "</div>"
            )
            self.add_html_block(block)
        except Exception as exc:
            self.add_message("bot", f"Failed to fetch students. Error: {exc}")

    def start(self):
        from pyodide.ffi import create_proxy  # type: ignore

        self.init_theme()
        self._load_saved_frontend_mode()

        async def on_send(_event=None):
            await self.handle_send()

        def on_keypress(event):
            if event.key == "Enter":
                asyncio.create_task(on_send())

        def on_help(_event):
            self.user_input.value = "help"
            asyncio.create_task(on_send())

        def on_theme(_event):
            self.toggle_theme()

        def on_modal_close(_event):
            self.close_modal()

        def on_modal_overlay_click(event):
            if event.target == self.student_form_modal:
                self.close_modal()

        async def on_form_submit(_event):
            await self.handle_form_submit()

        self.send_btn.addEventListener(
            "click", self._keep_proxy(create_proxy(lambda e: asyncio.create_task(on_send(e))))
        )
        self.user_input.addEventListener(
            "keypress", self._keep_proxy(create_proxy(on_keypress))
        )
        self.help_btn.addEventListener("click", self._keep_proxy(create_proxy(on_help)))
        self.theme_toggle.addEventListener("click", self._keep_proxy(create_proxy(on_theme)))
        self.modal_close.addEventListener("click", self._keep_proxy(create_proxy(on_modal_close)))
        self.cancel_form.addEventListener("click", self._keep_proxy(create_proxy(on_modal_close)))
        self.student_form_modal.addEventListener(
            "click", self._keep_proxy(create_proxy(on_modal_overlay_click))
        )
        self.student_form.addEventListener(
            "submit",
            self._keep_proxy(
                create_proxy(
                    lambda e: (e.preventDefault(), asyncio.create_task(on_form_submit(e)))
                )
            ),
        )

        self.add_message("bot", random.choice(GREETINGS))
        self.add_message("bot", "Python Student Bot is ready. Type help for commands.")

    async def handle_form_submit(self):
        submit_btn = self.student_form.querySelector(".btn-primary")
        submit_btn.classList.add("loading")

        data = {
            "Name": self.document.getElementById("studentName").value.strip(),
            "Department": self.document.getElementById("studentDept").value.strip(),
            "Year": self.document.getElementById("studentYear").value.strip(),
            "Section": self.document.getElementById("studentSection").value.strip().upper(),
            "Math": self.document.getElementById("marksMath").value.strip(),
            "Science": self.document.getElementById("marksScience").value.strip(),
            "English": self.document.getElementById("marksEnglish").value.strip(),
            "Programming": self.document.getElementById("marksProgramming").value.strip(),
            "Info": self.document.getElementById("studentInfo").value.strip(),
        }

        try:
            if self.form_mode == "update":
                target_name = self.update_target_name or data["Name"]
                await self.api.update_student(target_name, data)
                self.add_message("bot", f"Student {data['Name']} updated successfully.")
                self.toast("Student updated successfully", "success")
            else:
                await self.api.add_student(data)
                self.add_message("bot", f"Student {data['Name']} added successfully.")
                self.toast("Student added successfully", "success")

            self.close_modal()
        except Exception as exc:
            self.add_message("bot", f"Could not save student. Error: {exc}")
            self.toast("Failed to save student", "error")
        finally:
            submit_btn.classList.remove("loading")


def _run_cli_chatbot():
    RUNTIME_CONFIG.load_cli_env()
    backend_kind = RUNTIME_CONFIG.data_mode
    backend = None

    if backend_kind in {"local", "local-storage"}:
        backend = LocalExcelAPI(RUNTIME_CONFIG.local_excel_path)
    else:
        if not RUNTIME_CONFIG.sheetdb_api_url:
            raise RuntimeError(
                "DATA_MODE=sheetdb requires SHEETDB_API_URL in .env or environment variables"
            )

        class _SheetDBSyncAdapter:
            @staticmethod
            def add_student(data: dict):
                return asyncio.run(StudentSheetAPI.add_student(data))

            @staticmethod
            def update_student(name: str, data: dict):
                return asyncio.run(StudentSheetAPI.update_student(name, data))

            @staticmethod
            def get_student_by_name(name: str):
                return asyncio.run(StudentSheetAPI.get_student_by_name(name))

            @staticmethod
            def get_student_by_name_exact(name: str):
                return asyncio.run(StudentSheetAPI.get_student_by_name_exact(name))

            @staticmethod
            def suggest_student_names(name: str, limit: int = 5):
                return asyncio.run(StudentSheetAPI.suggest_student_names(name, limit))

            @staticmethod
            def get_student_total(name: str):
                return asyncio.run(StudentSheetAPI.get_student_total(name))

            @staticmethod
            def get_all_students():
                return asyncio.run(StudentSheetAPI.get_all_students())

        backend = _SheetDBSyncAdapter()

    def _print_student(student: dict):
        print("Chatbot: Here's what I found:")
        for key in STUDENT_COLUMNS:
            if key in student:
                print(f"{key}: {student.get(key, '')}")

    def _print_all(students: list[dict]):
        if not students:
            print("Chatbot: No students found in local Excel file.")
            return
        print(f"Chatbot: Found {len(students)} student(s):")
        for s in students:
            print(
                f"- {s.get('Name', '')} | {s.get('Department', '')} | Year {s.get('Year', '')} | "
                f"Sec {s.get('Section', '')} | Total {s.get('Total', 0)} | {s.get('Percentage', 0)}%"
            )

    def _collect_student_input(existing: dict | None = None) -> dict:
        existing = existing or {}

        def ask(prompt: str, key: str):
            current = str(existing.get(key, "")).strip()
            raw = input(f"{prompt}" + (f" [{current}]" if current else "") + ": ").strip()
            return raw if raw else current

        data = {
            "Name": ask("Enter name", "Name"),
            "Department": ask("Enter department", "Department"),
            "Year": ask("Enter year", "Year"),
            "Section": ask("Enter section", "Section"),
            "Math": ask("Enter Math marks", "Math"),
            "Science": ask("Enter Science marks", "Science"),
            "English": ask("Enter English marks", "English"),
            "Programming": ask("Enter Programming marks", "Programming"),
            "Info": ask("Enter Info about the student", "Info"),
        }

        for subject in ["Math", "Science", "English", "Programming"]:
            try:
                score = int(str(data[subject]).strip() or "0")
            except ValueError as exc:
                raise RuntimeError(f"Invalid numeric value for {subject}") from exc
            if not (0 <= score <= 100):
                raise RuntimeError(f"{subject} must be between 0 and 100")
            data[subject] = score

        return data

    print("Hi! Python Student Bot CLI mode")
    print(f"Active mode: {backend_kind}")
    if backend_kind == "local":
        print(f"Local Excel backend active: {RUNTIME_CONFIG.local_excel_path}")
    else:
        print("SheetDB backend active")
    print("Type 'exit' to quit.")

    while True:
        raw_input_value = input("You: ").strip()
        user_input = raw_input_value.lower()

        if user_input == "exit":
            print("Chatbot: Goodbye")
            break

        if user_input == "help":
            print(HELP_TEXT)
        elif user_input in {"hi", "hello", "hey"}:
            print("Chatbot:", random.choice(GREETINGS))
        elif "fact" in user_input or "joke" in user_input:
            print("Chatbot:", random.choice(FACTS))
        elif user_input.startswith("add a student") or user_input == "add student":
            try:
                data = _collect_student_input()
                student = backend.add_student(data)
                print(f"Chatbot: Student {student.get('Name', '')} added successfully in Excel.")
            except Exception as exc:
                print(f"Chatbot: Could not add student. Error: {exc}")
        elif user_input.startswith("update student"):
            name = raw_input_value[len("update student") :].strip()
            if not name:
                name = input("Enter exact student name to update: ").strip()
            try:
                existing = backend.get_student_by_name_exact(name)
                if not existing:
                    suggestions = backend.suggest_student_names(name)
                    if suggestions:
                        print("Chatbot: No exact match. Try one of these:")
                        for item in suggestions:
                            print(f"- {item}")
                    else:
                        print(f"Chatbot: No exact match found for '{name}'.")
                    continue

                print("Chatbot: Enter new values (press Enter to keep current value).")
                updated_data = _collect_student_input(existing)
                student = backend.update_student(name, updated_data)
                print(f"Chatbot: Student {student.get('Name', '')} updated successfully in Excel.")
            except Exception as exc:
                print(f"Chatbot: Could not update student. Error: {exc}")
        elif user_input.startswith("get student") or user_input.startswith("retrieve student"):
            if user_input.startswith("get student"):
                name = raw_input_value[len("get student") :].strip()
            else:
                name = raw_input_value[len("retrieve student") :].strip()
            if not name:
                name = input("Enter the student's name: ").strip()
            student = backend.get_student_by_name(name)
            if student:
                _print_student(student)
            else:
                print(f"Chatbot: No student found with the name {name}.")
        elif user_input.startswith("get total") or user_input.startswith("retrieve total"):
            if user_input.startswith("get total"):
                name = raw_input_value[len("get total") :].strip()
            else:
                name = raw_input_value[len("retrieve total") :].strip()
            if not name:
                name = input("Enter the student's name: ").strip()
            result = backend.get_student_total(name)
            if result:
                print(
                    f"Chatbot: The total marks for {result['name']} are {result['total']} and "
                    f"the percentage is {result['percentage']}%."
                )
            else:
                print(f"Chatbot: No student found with the name {name}.")
        elif "show all" in user_input or "all students" in user_input or "list students" in user_input:
            _print_all(backend.get_all_students())
        else:
            print("Chatbot: I'm not sure how to respond to that. Type 'help' to see commands.")


def _start_browser_app() -> bool:
    try:
        from pyscript import document  # type: ignore  # noqa: F401

        async def _bootstrap():
            app = BrowserChatApp()
            app.start()

            # Render UI first, then resolve configuration in background
            # so slow network requests do not delay first interaction.
            app.add_message("bot", "Loading configuration...")
            await RUNTIME_CONFIG.load_browser_env()
            app._bind_api_for_mode()
            app._load_saved_frontend_mode()
            app.add_message("bot", f"Active mode: {RUNTIME_CONFIG.data_mode}")

            if RUNTIME_CONFIG.mode_notice:
                app.add_message("bot", RUNTIME_CONFIG.mode_notice)

            if not RUNTIME_CONFIG.configured():
                app.add_message(
                    "bot",
                    "Configuration is missing. On GitHub Pages, type: "
                    "set sheetdb api YOUR_API_ID",
                )

        asyncio.create_task(_bootstrap())
        return True
    except Exception:
        return False


if not _start_browser_app() and __name__ == "__main__":
    try:
        _run_cli_chatbot()
    except KeyboardInterrupt:
        pass
