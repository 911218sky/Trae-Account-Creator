# Rule: Trae Account Creator Guidelines

You are an expert Python developer specializing in automation and browser testing.

## Project Overview
This project is an account creator tool using:
- **Language**: Python 3.12+
- **Package Manager**: `uv` (extremely fast pip replacement)
- **Automation**: `playwright` (Async API)
- **Build Tool**: `pyinstaller`
- **CI/CD**: GitHub Actions

## Coding Guidelines

### 1. Dependency Management
- ALWAYS use `uv` for dependency management.
- Install: `uv sync` or `uv pip install <package>`
- Run: `uv run <script.py>`

### 2. Playwright & Browser Automation
- Use **Async API** (`async_playwright`) for better concurrency.
- Handle `HEADLESS` mode via environment variables.
- **Critical**: For portable builds (PyInstaller), always check `sys.frozen` and set `PLAYWRIGHT_BROWSERS_PATH` correctly to support local `browsers/` folder.
  ```python
  if getattr(sys, 'frozen', False):
      base_dir = os.path.dirname(sys.executable)
      local_browsers_path = os.path.join(base_dir, 'browsers')
      if os.path.exists(local_browsers_path):
          os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_browsers_path
      else:
          os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
  ```

### 3. Email Handling
- Use `imaplib` for Gmail connections.
- Support **Cloudflare Email Routing** (catch-all domains).
- Implement strict recipient validation to avoid processing unrelated emails in the inbox.

### 4. Build & Release
- Releases are automated via GitHub Actions on tags starting with `v*`.
- Artifacts must be portable:
  - **Windows**: `.zip` (containing `.exe`, `.env.example`, `browsers/`)
  - **Linux/macOS**: `.tar.gz` (containing binary, `.env.example`, `browsers/`)
- NEVER commit `.env`, `accounts.txt`, `cookies/`, or `*.exe`.

### 5. Git Operations
- **MANDATORY**: Do NOT automatically commit or push changes to the remote repository.
- Always ask the user for confirmation before running `git commit` or `git push`.
- You may stage files (`git add`) but stop there and await user approval for the commit/push.

## Tone & Style
- Be concise and practical.
- Prioritize robust error handling (e.g., "Browser not found" hints).
- When suggesting commands, prefer `uv run ...`.
