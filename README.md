# Trae Account Creator

This tool automates the account creation process for Trae using a custom domain and Gmail IMAP for email verification.

## Using the Pre-built Release

You can download the tool from the [Releases](https://github.com/911218sky/Trae-Account-Creator/releases) page. We offer two versions:

1.  **Portable Version** (`-Portable`): Includes everything (executable + browsers). **Recommended for beginners.** No installation required, but file size is larger (~200MB).
2.  **Lite Version** (`-Lite`): Contains only the executable. **Small size (~20MB)**, but you must install Playwright browsers manually.

### Option 1: Portable Version (Recommended)
1.  Download `TraeAccountCreator-<OS>-Portable.zip` (or `.tar.gz`).
2.  Extract it.
3.  Configure `.env` (rename `.env.example`).
4.  Run `TraeAccountCreator.exe`.

### Option 2: Lite Version (Advanced)
1.  Download `TraeAccountCreator-<OS>-Lite.zip` (or `.tar.gz`).
2.  Extract it.
3.  Configure `.env`.
4.  **Install Browsers**:
    Open a terminal in the folder and run:
    ```powershell
    .\TraeAccountCreator.exe install-browsers
    ```
5.  Run the tool.

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

## Acknowledgements

This project draws inspiration from the community. Special thanks to the work here:
- Inspiration: https://github.com/S-Trespassing/Trae-Account-Creator

We appreciate the ideas and effort shared by the author.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPLv3) - see the [LICENSE](LICENSE) file for details.
