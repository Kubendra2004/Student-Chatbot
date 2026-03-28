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

   `DATA_MODE=sheetdb`

   `SHEETDB_API_URL=https://sheetdb.io/api/v1/your_api_id`

Optional local file backend path:

`LOCAL_EXCEL_PATH=chat.xlsx`

The app reads configuration from `.env`.
You can switch mode with `DATA_MODE`:

- `DATA_MODE=sheetdb`: use SheetDB backend
- `DATA_MODE=local`: use local backend

Hosted frontend behavior:

- On GitHub-hosted frontend, app forces `sheetdb` mode automatically.
- `local` mode is allowed only on `localhost`.
- If someone tries `set mode local` on GitHub Pages, a clear message is shown.

CLI local mode reads and updates the Excel file at `LOCAL_EXCEL_PATH` (default: `chat.xlsx`).
Frontend local mode reads/writes Excel through a local Python API server (`local_excel_api_server.py`).

## Commands

- `help`
- `hi` / `hello`
- `tell me a fact`
- `add a student`
- `update student <name>`
- `get student <name>`
- `get total <name>`
- `show all students`
- `set mode local`
- `set mode local-storage`
- `set mode sheetdb`
- `set sheetdb api YOUR_API_ID` (or full SheetDB URL)
- `reload env`
- `current mode`

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

To test local mode in browser, set:

`DATA_MODE=local`

Start the local Excel API server:

```powershell
pip install openpyxl
python local_excel_api_server.py
```

Then start the frontend static server in another terminal:

```powershell
python -m http.server 5500
```

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
- First load can take longer than a normal JS page because PyScript downloads Python runtime files.
- The app now shows UI immediately and loads configuration in the background to reduce page-freeze issues.
- In hosted mode, the SheetDB API key is saved in browser local storage and reused on next load.
