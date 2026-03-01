import sys
import asyncio
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from tkinter import ttk
from tkinter import font as tkfont
from PIL import Image, ImageDraw
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import register


class TextHandler(logging.Handler):
    def __init__(self, widget: tk.Text, max_lines: int = 2000):
        super().__init__()
        self.widget = widget
        self.max_lines = max_lines
        self.widget.configure(state="disabled")
        self.tag = "log"
        self.widget.tag_config(self.tag, foreground="#e6e6e6")
        self.widget.tag_config("log-debug", foreground="#9aa3ad")
        self.widget.tag_config("log-info", foreground="#e6e6e6")
        self.widget.tag_config("log-warning", foreground="#f5c542")
        self.widget.tag_config("log-error", foreground="#ff5e5e")
        self.widget.tag_config("log-critical", foreground="#ff3b3b")

    def emit(self, record: logging.LogRecord):
        msg = self.format(record) + "\n"
        def append():
            self.widget.configure(state="normal")
            level = record.levelno
            tag = (
                "log-critical" if level >= logging.CRITICAL else
                "log-error" if level >= logging.ERROR else
                "log-warning" if level >= logging.WARNING else
                "log-debug" if level <= logging.DEBUG else
                "log-info"
            )
            self.widget.insert(tk.END, msg, tag)
            self.widget.see(tk.END)
            try:
                lines = int(self.widget.index("end-1c").split(".")[0])
                if lines > self.max_lines:
                    drop = lines - self.max_lines
                    self.widget.delete("1.0", f"{drop}.0")
            except Exception:
                pass
            self.widget.configure(state="disabled")
        self.widget.after(0, append)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        try:
            self.title("Environment Settings")
        except Exception:
            pass
        self.parent = parent
        self.resizable(False, False)
        self.transient(parent)
        try:
            self.grab_set()
        except Exception:
            pass
        
        # Center the window
        try:
            self.place_window_center()
        except Exception:
            try:
                self.update_idletasks()
                w = 500
                h = 450
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = (sw // 2) - (w // 2)
                y = (sh // 2) - (h // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")
            except Exception:
                pass
        
        self.env_path = Path(".env")
        self.env_data = self._load_env()
        
        self._setup_ui()
        
    def _load_env(self):
        data = {}
        if self.env_path.exists():
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip()
        return data
        
    def _setup_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)
        
        # Title
        ttk.Label(container, text="Application Settings", font=("Segoe UI", 14, "bold"), foreground="#00FF99").pack(anchor="w", pady=(0, 20))
        
        # Form
        self.entries = {}
        
        # Gmail Settings
        group1 = ttk.LabelFrame(container, text="Gmail IMAP Configuration", padding=15, style="Card.TLabelframe")
        group1.pack(fill="x", pady=(0, 15))
        
        self._add_entry(group1, "EMAIL_USER", "Email Address")
        self._add_entry(group1, "EMAIL_PASS", "App Password", show="*")
        
        # Domain Settings
        group2 = ttk.LabelFrame(container, text="Custom Domain", padding=15, style="Card.TLabelframe")
        group2.pack(fill="x", pady=(0, 15))
        
        self._add_entry(group2, "CUSTOM_DOMAIN", "Domain (e.g., example.com)")
        
        # Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        tb.Button(btn_frame, text="Save & Reload", bootstyle="success", command=self._save).pack(side="right", padx=(10, 0))
        tb.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self.destroy).pack(side="right")
        
    def _add_entry(self, parent, key, label, show=None):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)
        
        ttk.Label(frame, text=label, width=20).pack(side="left")
        
        var = tk.StringVar(value=self.env_data.get(key, ""))
        entry = tb.Entry(frame, textvariable=var, show=show)
        entry.pack(side="left", fill="x", expand=True)
        
        self.entries[key] = var
        
    def _save(self):
        # Update existing env file preserving comments
        new_lines = []
        keys_written = set()
        
        if self.env_path.exists():
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        new_lines.append(line)
                        continue
                    
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        if k in self.entries:
                            new_lines.append(f"{k}={self.entries[k].get()}\n")
                            keys_written.add(k)
                        else:
                            new_lines.append(line)
        
        # Append new keys
        for k, var in self.entries.items():
            if k not in keys_written:
                new_lines.append(f"{k}={var.get()}\n")
                
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        # Reload env and settings
        load_dotenv(override=True)
        self.parent.settings = register.Settings.load()
        messagebox.showinfo("Success", "Settings saved and reloaded successfully!")
        self.destroy()


class App(tb.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Trae Account Creator")
        self.geometry("960x640")
        self.resizable(True, True)

        self.logger = logging.getLogger("register")
        self._set_icon()
        self._apply_styles()
        self._setup_ui()
        self._setup_logging()
        self.settings = register.Settings.load()
        self.running = False
    
    def _apply_styles(self):
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(size=10, family="Segoe UI")
        except Exception:
            pass
        style = tb.Style()
        
        # Define colors matching the green icon
        accent_color = "#00FF99"  # Bright green
        bg_color = "#191919"      # Dark background
        fg_color = "#FFFFFF"      # White text
        
        # Configure custom styles
        style.configure("TLabel", foreground=fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", foreground=accent_color, font=("Segoe UI", 18, "bold"))
        style.configure("Status.TLabel", foreground="#AAAAAA", font=("Segoe UI", 9))
        
        style.configure("Card.TLabelframe", background=bg_color, relief="solid", borderwidth=1, bordercolor="#333333")
        style.configure("Card.TLabelframe.Label", foreground=accent_color, font=("Segoe UI", 11, "bold"), background=bg_color)

        # Button styles
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))
        style.map("Action.TButton",
            foreground=[('pressed', 'black'), ('active', 'black')],
            background=[('pressed', accent_color), ('active', accent_color)]
        )

    def _set_icon(self):
        try:
            # Handle resource path for PyInstaller
            if getattr(sys, "frozen", False):
                base_dir = Path(sys._MEIPASS)
            else:
                base_dir = Path(__file__).resolve().parent
            
            assets_dir = base_dir / "assets"
            # Ensure assets directory exists only when not frozen (development)
            if not getattr(sys, "frozen", False):
                assets_dir.mkdir(exist_ok=True)
            
            ico_path = assets_dir / "app.ico"
            png_path = assets_dir / "app.png"
            
            # Generate icons if missing (only in development)
            if not getattr(sys, "frozen", False) and (not ico_path.exists() or not png_path.exists()):
                size = 256
                # Create base image (transparent)
                img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Colors
                bg_color = (25, 25, 25, 255)  # Dark gray/black
                accent_color = (0, 255, 153, 255)  # Bright green (#00FF99)
                
                # Background: Rounded rectangle
                padding = 24
                draw.rounded_rectangle(
                    [(padding, padding), (size - padding, size - padding)],
                    radius=60,
                    fill=bg_color
                )
                
                # Inner geometric shape: Rectangle border
                inner_padding = 64
                border_width = 24
                # Outer rectangle of the shape
                draw.rectangle(
                    [(inner_padding, inner_padding), (size - inner_padding, size - inner_padding)],
                    fill=accent_color
                )
                # Cut out the middle to make it a border
                draw.rectangle(
                    [(inner_padding + border_width, inner_padding + border_width), 
                     (size - inner_padding - border_width, size - inner_padding - border_width)],
                    fill=bg_color
                )
                
                # Two diamonds in the center
                center = size // 2
                diamond_size = 20
                offset = 30
                
                # Left diamond
                cx1, cy1 = center - offset, center
                draw.polygon([
                    (cx1, cy1 - diamond_size),
                    (cx1 + diamond_size, cy1),
                    (cx1, cy1 + diamond_size),
                    (cx1 - diamond_size, cy1)
                ], fill=accent_color)
                
                # Right diamond
                cx2, cy2 = center + offset, center
                draw.polygon([
                    (cx2, cy2 - diamond_size),
                    (cx2 + diamond_size, cy2),
                    (cx2, cy2 + diamond_size),
                    (cx2 - diamond_size, cy2)
                ], fill=accent_color)

                img.save(png_path)
                img.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                try:
                    icon = tk.PhotoImage(file=str(png_path))
                    self.iconphoto(True, icon)
                except Exception:
                    pass
        except Exception:
            pass
    def _setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Main container with padding
        main_container = ttk.Frame(self, padding=20)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Header Section
        header = ttk.Frame(main_container)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        header.columnconfigure(1, weight=1)
        
        # Title with Icon color accent
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")
        ttk.Label(title_frame, text="Trae", style="Header.TLabel").pack(side="left")
        ttk.Label(title_frame, text=" Account Creator", font=("Segoe UI", 18), foreground="#ffffff").pack(side="left")
        
        # Status Badge
        self.status_var = tk.StringVar(value="Ready")
        status_frame = ttk.Frame(header)
        status_frame.grid(row=0, column=2, sticky="e")
        ttk.Label(status_frame, text="Status: ", style="Status.TLabel").pack(side="left")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 9, "bold"), foreground="#00FF99")
        self.status_label.pack(side="left")
        
        # Settings Button (New)
        settings_btn = tb.Button(header, text="⚙ Settings", command=self._open_settings, bootstyle="link", cursor="hand2")
        settings_btn.grid(row=0, column=3, sticky="e", padx=(15, 0))

        # Content Area - Left Panel (Controls)
        left_panel = ttk.Frame(main_container)
        left_panel.grid(row=1, column=0, sticky="nsw", padx=(0, 20))
        left_panel.columnconfigure(0, weight=1)
        
        # Configuration Card
        config_frame = ttk.LabelFrame(left_panel, text="Configuration", style="Card.TLabelframe", padding=15)
        config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        config_frame.columnconfigure(1, weight=1)
        
        ttk.Label(config_frame, text="Total Accounts").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.total_var = tk.IntVar(value=1)
        ttk.Spinbox(config_frame, textvariable=self.total_var, from_=1, to=1000, width=15).grid(row=0, column=1, sticky="e", pady=(0, 5))
        
        ttk.Label(config_frame, text="Concurrency").grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.conc_var = tk.IntVar(value=1)
        ttk.Spinbox(config_frame, textvariable=self.conc_var, from_=1, to=50, width=15).grid(row=1, column=1, sticky="e", pady=(0, 5))
        
        self.headless_var = tk.BooleanVar(value=os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes", "y", "on"})
        ttk.Checkbutton(config_frame, text="Headless Mode (Background)", variable=self.headless_var, style="TCheckbutton").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Actions Card
        action_frame = ttk.LabelFrame(left_panel, text="Actions", style="Card.TLabelframe", padding=15)
        action_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        self.run_one_btn = tb.Button(action_frame, text="Register One", command=self._run_one, bootstyle="success-outline", width=15)
        self.run_one_btn.grid(row=0, column=0, padx=(0, 5), pady=(0, 10), sticky="ew")
        
        self.run_batch_btn = tb.Button(action_frame, text="Batch Register", command=self._run_batch, bootstyle="success", width=15)
        self.run_batch_btn.grid(row=0, column=1, padx=(5, 0), pady=(0, 10), sticky="ew")
        
        ttk.Separator(action_frame).grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.install_btn = tb.Button(action_frame, text="Install Browsers", command=self._install_browsers, bootstyle="info-outline", width=15)
        self.install_btn.grid(row=2, column=0, padx=(0, 5), sticky="ew")
        
        self.merge_btn = tb.Button(action_frame, text="Merge Accounts", command=self._merge_accounts, bootstyle="secondary-outline", width=15)
        self.merge_btn.grid(row=2, column=1, padx=(5, 0), sticky="ew")

        # Progress Section
        progress_frame = ttk.LabelFrame(left_panel, text="Progress", style="Card.TLabelframe", padding=15)
        progress_frame.grid(row=2, column=0, sticky="ew")
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = tb.Floodgauge(
            progress_frame, 
            bootstyle="success", 
            font=("Segoe UI", 8), 
            mask="{}%",
            orient="horizontal"
        )
        self.progress.pack(fill="x", expand=True)

        # Right Panel (Logs)
        right_panel = ttk.LabelFrame(main_container, text="System Logs", style="Card.TLabelframe", padding=2)
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            right_panel, 
            wrap="word", 
            bg="#111111", 
            fg="#e6e6e6", 
            insertbackground="#00FF99", 
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(right_panel, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _setup_logging(self):
        handler = TextHandler(self.log_text, max_lines=2000)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        if not any(isinstance(h, TextHandler) for h in self.logger.handlers):
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _open_settings(self):
        try:
            dlg = SettingsDialog(self)
            try:
                self.wait_window(dlg)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _set_running(self, val: bool):
        self.running = val
        state = "disabled" if val else "normal"
        # Disable buttons
        for btn in [self.run_one_btn, self.run_batch_btn, self.install_btn, self.merge_btn]:
            btn.configure(state=state)
            
        # Update Status
        if val:
            self.status_var.set("Running...")
            self.status_label.configure(foreground="#00FF99")
            self.progress.start()
        else:
            self.status_var.set("Ready")
            self.status_label.configure(foreground="#AAAAAA")
            self.progress.stop()
            self.progress.configure(value=0)


    def _apply_headless(self):
        os.environ["HEADLESS"] = "1" if self.headless_var.get() else "0"

    def _run_thread(self, target):
        def wrapper():
            try:
                target()
            finally:
                def reset():
                    try:
                        self.progress.stop()
                        self.progress.configure(maximum=100, value=0)
                    except Exception:
                        pass
                    self._set_running(False)
                self.after(0, reset)
        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    def _run_one(self):
        if self.running:
            return
        self._apply_headless()
        self._set_running(True)
        def task():
            try:
                def cb(done, total):
                    def upd():
                        self.progress.configure(maximum=total, value=done)
                    self.progress.after(0, upd)
                asyncio.run(register.run_batch(1, 1, self.settings, progress_cb=cb))
            except Exception as e:
                messagebox.showerror("Error", str(e))
        self._run_thread(task)

    def _run_batch(self):
        if self.running:
            return
        total = max(1, int(self.total_var.get()))
        conc = max(1, int(self.conc_var.get()))
        self._apply_headless()
        self._set_running(True)
        def task():
            try:
                def cb(done, total_):
                    def upd():
                        self.progress.configure(maximum=total_, value=done)
                    self.progress.after(0, upd)
                asyncio.run(register.run_batch(total, conc, self.settings, progress_cb=cb))
            except Exception as e:
                messagebox.showerror("Error", str(e))
        self._run_thread(task)

    def _install_browsers(self):
        if self.running:
            return
        self._set_running(True)
        def task():
            try:
                def pcb(pct):
                    def upd():
                        self.progress.configure(maximum=100, value=max(0, min(100, pct)))
                    self.progress.after(0, upd)
                register.install_playwright_browsers("chromium", progress_cb=pcb)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        self._run_thread(task)

    def _merge_accounts(self):
        if self.running:
            return
        initial = f"accounts_merged-{time.strftime('%Y-%m-%d')}.json"
        file_path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=initial, filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        self._set_running(True)
        def task():
            try:
                out = Path(file_path)
                register.merge_accounts_command(self.settings.accounts_dir, out)
            except Exception as e:
                messagebox.showerror("錯誤", str(e))
        self._run_thread(task)


def main():
    if len(sys.argv) > 1:
        # If there are command line arguments, pass them to register.main
        # This handles the internal browser installation in frozen mode
        import register
        sys.exit(register.main(sys.argv[1:]))
    
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
