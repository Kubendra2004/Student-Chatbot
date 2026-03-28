# Student Bot (Python-Only, GitHub Pages Ready)

This project now runs the chatbot logic in Python in the browser using PyScript.

- Frontend shell: HTML + CSS
- Main application logic: Python (`bot.py`)
- Database: Google Sheets via SheetDB REST API
- Hosting target: GitHub Pages

## What Changed

- Removed runtime dependency on the JavaScript app files.
- `index.html` now loads PyScript and runs `bot.py` directly.
- `bot.py` now handles:
  - chat command parsing
  - Google Sheets data operations through SheetDB
  - rendering chat/table UI output in the page

## Google Sheets + SheetDB Setup

1. Create a Google Sheet with these headers:

   `Name, Department, Year, Section, Math, Science, English, Programming, Info, Total, Percentage`

2. Create an API in SheetDB connected to that sheet.
3. Copy your SheetDB endpoint, for example:

   `https://sheetdb.io/api/v1/your_api_id`

4. Copy `.env.example` to `.env` and set:

   `SHEETDB_API_URL=https://sheetdb.io/api/v1/your_api_id`

Optional local file backend path:

`LOCAL_EXCEL_PATH=chat.xlsx`

The app reads `SHEETDB_API_URL` from `.env` in browser mode and CLI mode.
CLI local mode reads and updates the Excel file at `LOCAL_EXCEL_PATH` (default: `chat.xlsx`).

## Commands

- `help`
- `hi` / `hello`
- `tell me a fact`
- `add a student`
- `get student <name>`
- `get total <name>`
- `show all students`

Update behavior:

- `update student <name>` now requires an exact student name match (case-insensitive).
- If exact match fails, the bot suggests close student names to help you pick the right one.

## Run Locally

You can test quickly using a local static server:

```powershell
python -m http.server 5500
```

Then open:

`http://localhost:5500`

Local Excel CLI mode:

```powershell
pip install openpyxl
python bot.py
```

This mode supports add/update/get/total/show-all directly in the local Excel file.

## Deploy on GitHub Pages

1. Push this project to GitHub.
2. In repository settings, open Pages.
3. Set source to your main branch (root folder).
4. Save and wait for deployment.

Your bot will run fully client-side with Python through PyScript.

## Notes

- GitHub Pages cannot run a Python backend server.
- This approach works because Python runs in the browser (PyScript/Pyodide).
- On GitHub Pages, files are public static assets. If you publish `.env`, your SheetDB URL is public.
