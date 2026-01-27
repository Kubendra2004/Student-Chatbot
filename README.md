<div align="center">

# 🤖 Student Bot

### An Interactive Student Information Chatbot

[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Google Sheets](https://img.shields.io/badge/Google%20Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)](https://www.google.com/sheets/about/)

<br>

![Dark Mode](https://img.shields.io/badge/Theme-Dark%20Mode-0f172a?style=flat-square)
![Light Mode](https://img.shields.io/badge/Theme-Light%20Mode-f8fafc?style=flat-square)
![Responsive](https://img.shields.io/badge/Responsive-Mobile%20Ready-10b981?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)

---

**A modern, feature-rich chatbot for managing student records with a stunning UI and real-time Google Sheets integration.**

[Live Demo](#-live-demo) • [Features](#-features) • [Quick Start](#-quick-start) • [Commands](#-commands)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎨 Modern Design
- Glassmorphism UI with gradient accents
- Smooth animations & transitions
- Floating background shapes
- Beautiful data tables

</td>
<td width="50%">

### 🌓 Theme Support
- Dark / Light mode toggle
- Automatic theme persistence
- System preference detection
- Smooth theme transitions

</td>
</tr>
<tr>
<td width="50%">

### 💬 Smart Chat
- Natural language commands
- Typing indicators
- Enter to send
- Toast notifications

</td>
<td width="50%">

### 📊 Data Management
- Add / Update students
- View individual records
- List all students
- Auto-calculated grades

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1️⃣ Set Up Google Sheets

Create a new Google Sheet with these columns:

| Name | Department | Year | Section | Math | Science | English | Programming | Info | Total | Percentage |
|------|------------|------|---------|------|---------|---------|-------------|------|-------|------------|

### 2️⃣ Connect to SheetDB

1. Go to [SheetDB.io](https://sheetdb.io/) and sign up (free)
2. Click **"Create new API"**
3. Paste your Google Sheets URL
4. Copy your API ID

### 3️⃣ Configure the Bot

Edit `js/config.js` and replace `YOUR_API_ID`:

```javascript
SHEETDB_API_URL: 'https://sheetdb.io/api/v1/YOUR_API_ID',
```

### 4️⃣ Launch

Simply open `index.html` in your browser! 🎉

---

## 💬 Commands

| Command | Description |
|---------|-------------|
| `help` | 📖 Show all available commands |
| `add a student` | ➕ Open form to add new student |
| `get student [name]` | 🔍 View student information |
| `get total [name]` | 📊 View marks and percentage |
| `show all students` | 📋 List all student records |
| `hi` / `hello` | 👋 Get a friendly greeting |
| `tell me a fact` | 🎲 Get a random fun fact |

---

## 📁 Project Structure

```
Student-Chatbot/
├── 📄 index.html           # Main page
├── 📁 css/
│   └── 🎨 styles.css       # Themes & animations
├── 📁 js/
│   ├── ⚙️ config.js        # Configuration
│   ├── 🌓 theme.js         # Theme manager
│   ├── 🔌 api.js           # SheetDB integration
│   ├── 🤖 chatbot.js       # Bot logic
│   └── 🎮 app.js           # Main controller
└── 📖 README.md            # Documentation
```

---

## 🛠️ Tech Stack

<div align="center">

| Technology | Purpose |
|------------|---------|
| ![HTML5](https://img.shields.io/badge/-HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) | Structure & Semantics |
| ![CSS3](https://img.shields.io/badge/-CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) | Styling & Animations |
| ![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) | Logic & Interactivity |
| ![Google Sheets](https://img.shields.io/badge/-Google%20Sheets-34A853?style=flat-square&logo=google-sheets&logoColor=white) | Database Storage |
| ![SheetDB](https://img.shields.io/badge/-SheetDB-4285F4?style=flat-square&logo=google&logoColor=white) | REST API Layer |

</div>

---

## 🎨 Customization

### Change Theme Colors

Edit CSS variables in `css/styles.css`:

```css
:root {
    --primary: #6366f1;      /* Accent color */
    --bg-primary: #0f172a;   /* Background */
    --success: #10b981;      /* Success state */
}
```

### Add Greetings

Edit the `GREETINGS` array in `js/config.js`:

```javascript
GREETINGS: [
    "Your custom greeting! 🎉",
    // ... add more
],
```

---

## 📸 Screenshots

<div align="center">

| Dark Mode | Light Mode |
|-----------|------------|
| Coming Soon | Coming Soon |

</div>

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ by [Kubendra](https://github.com/Kubendra2004)**

⭐ Star this repo if you found it helpful!

</div>
