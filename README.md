# Trae Account Creator

Automated Trae account registration tool using custom domain and Gmail IMAP for email verification.

## Installation

```bash
# Install uv (Python package manager)
pip install uv

# Install dependencies
uv sync

# Install browser
uv run playwright install chromium
```

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
```

## Account Management

After registration, the tool saves session tokens and cookies in the `cookies/` directory as JSON files. You can use these credentials with [Trae-Account-Manager](https://github.com/Yang-505/Trae-Account-Manager) to manage and use your accounts.

Each session file contains:
- `token`: Authentication token for API access
- `cookie`: Session cookie string for browser access

## License

GNU Affero General Public License v3.0 (AGPLv3)
