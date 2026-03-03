# Trae Account Creator

<div align="center">
  <img src="assets/app.png" alt="Trae Account Creator" width="128" />
  <br />
  <p><b>Automated Trae account registration tool using Custom Domains and Gmail IMAP.</b></p>
</div>

## 📖 Overview

**Trae Account Creator** is a robust automation tool designed to streamline the registration process for Trae accounts. By leveraging custom domains and Gmail IMAP for email verification, it fully automates the account creation workflow.

The tool features a modern GUI for ease of use, alongside a powerful CLI for batch operations, making it suitable for both individual and bulk account management.

## ✨ Key Features

- **Full Automation**: Handles form filling, email verification code retrieval, and registration automatically.
- **User-Friendly GUI**: A clean, intuitive desktop interface for managing tasks without command-line knowledge.
- **Batch Processing**: Supports concurrent registration threads for high-efficiency bulk creation.
- **Portable Architecture**: Browsers and dependencies are managed locally within the project, ensuring no interference with the system environment.
- **Account Management**: Automatically saves credentials and includes utilities to merge and export account data.

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **uv** (An extremely fast Python package installer and resolver)

```bash
# Install uv
pip install uv
```

### Installation

Clone the repository and initialize the project environment:

```bash
# Install dependencies
uv sync

# Install the required local browser (Chromium)
uv run python register.py install-browsers chromium
```

### ⚙️ Configuration

Copy `.env.example` to a new file named `.env` in the root directory and configure your credentials.

**Required `.env` settings:**

```ini
# Gmail IMAP Configuration (for receiving verification codes)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password

# Custom Domain (Must be configured with Cloudflare Email Routing)
CUSTOM_DOMAIN=your_domain.com
```

> **Security Note**: `EMAIL_PASS` must be a **Google App Password**, not your standard Gmail login password. You can generate one in your Google Account settings under [App passwords](https://myaccount.google.com/apppasswords).

## 💻 Usage

### Graphical User Interface (Recommended)

The easiest way to use the tool is via the built-in GUI:

```bash
uv run python gui.py
```

### Command Line Interface (CLI)

For advanced users or automation scripts:

```bash
# Register a single account
uv run register.py

# Batch registration (e.g., 10 accounts with 2 concurrent threads)
uv run register.py 10 2
```

## 📂 Account Management

### Data Storage
Successfully registered accounts are saved as individual JSON files in the `accounts/` directory:
- `accounts/user1@domain.com.json`
- `accounts/user2@domain.com.json`

### Merging Accounts
To consolidate all registered accounts into a single file (compatible with import tools):

```bash
uv run python register.py merge-accounts
```
*This creates a timestamped file, e.g., `accounts_merged-2026-03-01.json`.*

## 🔗 Integration

The generated JSON files are fully compatible with [Trae Account Manager](https://github.com/911218sky/Trae-Account-Creator). You can import the merged JSON file directly to manage your accounts centrally.

## ⚠️ Disclaimer

This project is for educational and research purposes only. It is inspired by [S-Trespassing/Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator).

**License**: AGPLv3
