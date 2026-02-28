# Trae Account Creator

This tool automates the account creation process for Trae using a custom domain and Gmail IMAP for email verification.

## Using the Pre-built Release (Portable)

You can download a fully portable version from the [Releases](https://github.com/911218sky/Trae-Account-Creator/releases) page. This version includes everything you need (executable + browsers).

### 1. Download & Extract
1.  Go to the **Releases** page.
2.  Download the archive for your OS:
    *   **Windows**: `.zip`
    *   **Linux/macOS**: `.tar.gz`
3.  **Extract the file** to a folder.

### 2. Configuration
Inside the extracted folder, you will find `.env.example`.
1.  Rename `.env.example` to `.env`.
2.  Open `.env` with a text editor (Notepad, VS Code, etc.) and fill in your details:

```ini
# Gmail IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password  # The 16-char App Password

# Custom Domain Configuration (Cloudflare Email Routing)
CUSTOM_DOMAIN=your_domain.com

# Browser Configuration
HEADLESS=false
```

### 3. Run the Tool
Simply double-click `TraeAccountCreator.exe` or run it from the terminal. **No installation required.**

```powershell
# Run single account registration
.\TraeAccountCreator.exe

# Run batch registration
.\TraeAccountCreator.exe 10 2
```

> **Note:** The `browsers` folder included in the zip allows the tool to run without installing Playwright separately. Do not delete it.

---

## Development Setup

If you want to modify the code or build it yourself, follow these steps.

## Prerequisites

- **Python**: Ensure you have Python installed (Python 3.12+ recommended).
- **uv**: An extremely fast Python package installer and resolver.
  ```bash
  # Install uv
  pip install uv
  ```

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory.

2. **Sync dependencies using uv**:
   ```powershell
   # This creates the .venv and installs dependencies from uv.lock
   uv sync
   ```

3. **Install Playwright browsers**:
   ```powershell
   uv run playwright install chromium
   ```

## Configuration

You need to configure your email settings in the `.env` file.

### 1. Gmail Configuration (IMAP)

This tool uses Gmail's IMAP server to fetch verification codes.

1.  **Enable 2-Step Verification**: Go to your [Google Account Security](https://myaccount.google.com/security) settings and enable "2-Step Verification".
2.  **Generate App Password**:
    *   Go to [App passwords](https://myaccount.google.com/apppasswords).
    *   Create a new app password (name it "Trae Auto" or similar).
    *   Copy the 16-character password (without spaces).

### 2. Cloudflare Email Routing (Custom Domain)

To generate unlimited email addresses (e.g., `random@yourdomain.com`), you need a custom domain managed by Cloudflare.

1.  **Enable Email Routing**:
    *   Log in to Cloudflare and select your domain.
    *   Go to **Email** > **Email Routing**.
    *   Click "Get Started" or "Enable Email Routing".
2.  **Configure Catch-All Rule**:
    *   In Email Routing settings, go to **Routing rules**.
    *   Enable **Catch-all address**.
    *   Set the **Action** to "Send to" and enter your **Gmail address** (the one configured in step 1).
    *   Ensure the status is "Active".

### 3. Update .env File

Create or edit the `.env` file in the project root:

```ini
# Gmail IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password  # The 16-char App Password

# Custom Domain Configuration
CUSTOM_DOMAIN=your_domain.com
```

## Usage

Run the registration script using `uv run`:

```powershell
uv run register.py
```

### Batch Registration

You can specify the number of accounts to create and the concurrency level:

```powershell
# Format: uv run register.py [total_accounts] [concurrency]
uv run register.py 10 2
```

## How It Works

1.  **Email Generation**: The script generates a random email address like `x7z9k2@yourdomain.com`.
2.  **Registration**: It uses Playwright to automate the sign-up process on the Trae website.
3.  **Verification**:
    *   Trae sends a verification code to `x7z9k2@yourdomain.com`.
    *   Cloudflare forwards this email to your real Gmail address.
    *   The script checks your Gmail inbox via IMAP, finds the email sent *to* the generated address, and extracts the code.
4.  **Completion**: The script submits the code and completes the registration.

## Troubleshooting

### "Executable doesn't exist" Error
If you see an error like `BrowserType.launch: Executable doesn't exist...`, it means the bundled Playwright cannot find the browser binaries.

**Solution:**
Open a terminal in the same folder as the `.exe` and run:
```powershell
# For Windows
.\TraeAccountCreator.exe install-browsers
# OR manually install playwright
uv run playwright install chromium
```
*Note: We are working on bundling the browser or automating this step.*

Currently, the easiest way is to ensure you have Playwright browsers installed on your system. If you are using the standalone `.exe` on a clean machine, you might need to install the browsers first.

### Missing .env file
Ensure you have a `.env` file in the same directory as the executable. You can copy `.env.example` to `.env` and fill in your details.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPLv3) - see the [LICENSE](LICENSE) file for details.
