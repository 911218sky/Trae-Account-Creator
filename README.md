# Trae Account Creator

Automated Trae account registration tool using custom domain and Gmail IMAP for email verification.

## Installation

```bash
# Install uv (Python package manager)
pip install uv

# Install dependencies
uv sync

# Install Chromium browser only (lightweight)
uv run playwright install chromium
```

> **Note**: We only install Chromium to keep the installation lightweight (~150MB vs ~300MB for all browsers).

## Configuration

Copy `.env.example` to `.env` and fill in the following:

```ini
# Gmail IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password  # Gmail App Password

# Custom Domain (requires Cloudflare Email Routing)
CUSTOM_DOMAIN=your_domain.com
```

### Gmail App Password Setup

1. Enable [2-Step Verification](https://myaccount.google.com/security)
2. Go to [App passwords](https://myaccount.google.com/apppasswords) and generate a password
3. Copy the 16-character password to `EMAIL_PASS` in `.env`

### Cloudflare Email Routing Setup

1. Log in to Cloudflare and select your domain
2. Go to **Email** > **Email Routing**
3. Enable **Catch-all address** and forward to your Gmail

## Usage

```bash
# Register single account
uv run register.py

# Batch registration (total concurrent)
uv run register.py 10 2

# Merge all accounts into a single JSON file
uv run register.py merge-accounts

# Merge with custom output file
uv run register.py merge-accounts --output my_accounts.json
```

For the compiled `.exe` version:
```bash
# Register accounts
TraeAccountCreator.exe
TraeAccountCreator.exe 10 2

# Merge accounts
TraeAccountCreator.exe merge-accounts
TraeAccountCreator.exe merge-accounts --output my_accounts.json
```

## Account Management

After registration, account data is saved in the `accounts/` directory. Each account is stored as a separate JSON file named after the email address.

### File Structure
```
accounts/
├── user123_example_com.json
├── user456_example_com.json
└── test_domain_com.json
```

### Merge All Accounts

The merge functionality is now built into the main tool:

```bash
# Using Python
uv run python register.py merge-accounts

# Using compiled .exe
TraeAccountCreator.exe merge-accounts

# Custom output file
uv run python register.py merge-accounts --output my_accounts.json
```

This creates a single JSON file containing all accounts in an array format, making it easier to process or import into other tools.

**Note:** The standalone `merge_accounts.py` script is still available for advanced use cases.

### Import to Trae Account Manager

1. Open [Trae-Account-Manager](https://github.com/Yang-505/Trae-Account-Manager)
2. Navigate to **Settings** page
3. Click **Import Data** button
4. Select JSON files from the `accounts/` folder (or use the merged file)
5. All account information will be imported automatically

You can import individual files, select multiple files at once, or use the merged `accounts_merged.json` for batch import.

## Acknowledgements

This project is inspired by and references [S-Trespassing/Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator). Special thanks to the original author for the inspiration and foundation.

## License

GNU Affero General Public License v3.0 (AGPLv3)
