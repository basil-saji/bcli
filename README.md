# BCLI – Terminal Real-Time Communication

```text
██████╗  ██████╗██╗     ██╗
██╔══██╗██╔════╝██║     ██║
██████╔╝██║     ██║     ██║
██╔══██╗██║     ██║     ██║
██████╔╝╚██████╗███████╗██║
╚═════╝  ╚═════╝╚══════╝╚═╝
```

**BCLI** is a lightweight, high-performance terminal chat and file-sharing tool powered by Supabase Realtime and Python.

---

## 🚀 Features

- **Real-Time Messaging** – Instant synchronization via Supabase  
- **Code Mode** – Multiline support with preserved indentation  
- **File Sharing** – Share images, PDFs, and scripts (auto-saves to `downloads/`)  
- **Auto-Updates** – Automatically pulls the latest release from GitHub  
- **Self-Destruct** – Wipes all trace of the program with `;kill -s`  

---

## 📥 Installation

### Windows (PowerShell)

```powershell
iwr https://raw.githubusercontent.com/basil-saji/bcli/main/install.ps1 | iex
```

### Linux / macOS (Bash)

```bash
curl -sSL https://raw.githubusercontent.com/basil-saji/bcli/main/install.sh | bash
```

---

## 🛠 Usage

After installation, simply run:

```bash
bcli
```

---

## 📋 Commands

| Command        | Description |
|---------------|------------|
| `;code`       | Enter multiline code mode |
| `;send [file]`| Share a file or image |
| `;guide`      | View full user guide |
| `;kill -s`    | Uninstall and wipe data |

---

## 🔗 Repository

https://github.com/basil-saji/bcli  

Developed by **Basil Saji**

---

## ✅ Final Publication Checklist

1. **Update `broadcaster.py`** – Ensure it includes the chunking logic.  
2. **Add `VERSION`** – Create a file containing only:
   ```
   1.0.0
   ```
3. **Add `GUIDE.txt` and `README.md`** – Use this finalized text.  
4. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Complete production bundle with banner and guides"
   git push origin main
   ```
````
