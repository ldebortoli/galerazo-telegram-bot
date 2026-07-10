from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .instance_lock import SingleInstance


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PID_PATH = DATA_DIR / "bot.pid"
LOG_PATH = DATA_DIR / "bot.log"
ENV_PATH = PROJECT_ROOT / ".env"
ICON_PNG_PATH = PROJECT_ROOT / "assets" / "galerazo-bot-icon.png"
ICON_ICO_PATH = PROJECT_ROOT / "assets" / "galerazo-bot-icon.ico"
WINDOWS_APP_ID = "GalerazoBot.ControlPanel"

FIELDS = (
    ("TELEGRAM_BOT_TOKEN", "Token del bot", True),
    ("TELEGRAM_DEV_USER_IDS", "IDs de desarrolladores", False),
    ("TELEGRAM_LOG_CHAT_ID", "ID del canal de logs", False),
    ("TELEGRAM_ANNOUNCEMENTS_CHAT_ID", "ID del canal de anuncios", False),
    ("DATABASE_PATH", "Base de datos", False),
    ("GOOGLE_SHEETS_CREDENTIALS_JSON_PATH", "Credenciales de Google", False),
    ("GOOGLE_SHEETS_SPREADSHEET_ID", "ID de Google Sheet", False),
    ("GOOGLE_SHEETS_WORKSHEET_NAME", "Hoja de gastos", False),
)


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env(changes: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pending = dict(changes)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in pending:
                output.append(f"{key}={pending.pop(key)}")
                continue
        output.append(line)
    if output and output[-1]:
        output.append("")
    output.extend(f"{key}={value}" for key, value in pending.items())
    ENV_PATH.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def _running_process_id() -> int | None:
    try:
        pid = int(PID_PATH.read_text(encoding="ascii").strip())
        if _is_process_running(pid):
            return pid
    except (FileNotFoundError, ValueError):
        pass
    PID_PATH.unlink(missing_ok=True)
    return None


def _is_process_running(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except (PermissionError, ProcessLookupError, OSError):
            return False

    process_query_limited_information = 0x1000
    still_active = 259
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, wintypes.LPDWORD)
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


class ControlPanel(tk.Tk):
    BG = "#0c1725"
    PANEL = "#111f31"
    TEXT = "#eff7ff"
    MUTED = "#96abc4"
    BORDER = "#37485e"
    GREEN = "#34d399"
    RED = "#f43f5e"
    AMBER = "#facc15"

    def __init__(self) -> None:
        super().__init__()
        self.title("Galerazo Bot - Control")
        self.geometry("760x690")
        self.minsize(680, 620)
        self.configure(bg=self.BG)
        self.variables: dict[str, tk.StringVar] = {}
        self.starting_process: subprocess.Popen[str] | None = None
        self.startup_log_offset = 0
        self._set_window_icon()
        self._configure_styles()
        self._build_ui()
        self.load_configuration()
        self.refresh_status()
        self.after(1500, self._status_tick)

    def _set_window_icon(self) -> None:
        if ICON_PNG_PATH.exists():
            self.window_icon = tk.PhotoImage(file=ICON_PNG_PATH)
            self.iconphoto(True, self.window_icon)
        if os.name == "nt" and ICON_ICO_PATH.exists():
            self.iconbitmap(default=str(ICON_ICO_PATH))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=self.MUTED)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22))
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 12))
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.PANEL, foreground=self.MUTED, padding=(14, 8), font=("Segoe UI", 10))
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.BORDER)],
            foreground=[("selected", self.TEXT)],
            padding=[("selected", (20, 11))],
            font=[("selected", ("Segoe UI Semibold", 11))],
        )
        style.configure("TEntry", fieldbackground="#17283d", foreground=self.TEXT, insertcolor=self.TEXT, bordercolor=self.BORDER, padding=8)
        style.configure("TButton", background="#1c293a", foreground=self.TEXT, bordercolor=self.BORDER, padding=(14, 9))
        style.map("TButton", background=[("active", "#293a50"), ("disabled", self.PANEL)])
        style.configure("Start.TButton", background="#14745b")
        style.map("Start.TButton", background=[("active", "#18896b")])
        style.configure("Stop.TButton", background="#b42d40")
        style.map("Stop.TButton", background=[("active", "#cf344a")])

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=28)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Galerazo Bot", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text=str(PROJECT_ROOT), style="Muted.TLabel").pack(anchor="w", pady=(2, 18))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.control_tab = ttk.Frame(self.notebook, padding=(4, 22))
        self.config_tab = ttk.Frame(self.notebook, padding=(4, 20))
        self.logs_tab = ttk.Frame(self.notebook, padding=(4, 20))
        self.notebook.add(self.control_tab, text="Control")
        self.notebook.add(self.config_tab, text="Configuracion")
        self.notebook.add(self.logs_tab, text="Logs")
        self._build_control_tab(self.control_tab)
        self._build_config_tab(self.config_tab)
        self._build_logs_tab(self.logs_tab)

    def _build_control_tab(self, parent: ttk.Frame) -> None:
        status = ttk.Frame(parent, style="Panel.TFrame", padding=22)
        status.pack(fill="x")
        status.columnconfigure(1, weight=1)
        self.status_dot = tk.Canvas(status, width=16, height=16, bg=self.PANEL, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, padx=(0, 12), sticky="w")
        self.status_circle = self.status_dot.create_oval(1, 1, 15, 15, fill=self.RED, outline="")
        self.status_label = ttk.Label(status, text="BOT APAGADO", style="Status.TLabel", background=self.PANEL)
        self.status_label.grid(row=0, column=1, sticky="w")
        self.detail_label = ttk.Label(status, text="", style="Muted.TLabel", background=self.PANEL)
        self.detail_label.grid(row=1, column=1, sticky="w", pady=(5, 0))

        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=20)
        buttons.columnconfigure((0, 1, 2), weight=1)
        self.start_button = ttk.Button(buttons, text="Encender", style="Start.TButton", command=self.start_bot)
        self.stop_button = ttk.Button(buttons, text="Apagar", style="Stop.TButton", command=self.stop_bot)
        self.restart_button = ttk.Button(buttons, text="Reiniciar", command=self.restart_bot)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=6)
        self.restart_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        ttk.Button(parent, text="Actualizar estado", command=self.refresh_status).pack(fill="x")
        ttk.Label(parent, text="Cerrar este panel no apaga el bot. Usa el boton Apagar.", style="Muted.TLabel").pack(anchor="w", pady=(18, 0))

    def _build_config_tab(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        for row, (key, label, secret) in enumerate(FIELDS):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=6)
            variable = tk.StringVar()
            self.variables[key] = variable
            entry = ttk.Entry(form, textvariable=variable, show="*" if secret else "")
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            if secret:
                ttk.Button(form, text="Mostrar", width=9, command=lambda item=entry: self._toggle_secret(item)).grid(row=row, column=2, padx=(8, 0))
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(16, 0))
        ttk.Button(actions, text="Guardar configuracion", command=self.save_configuration).pack(side="left")
        ttk.Button(actions, text="Recargar", command=self.load_configuration).pack(side="left", padx=8)
        ttk.Button(actions, text="Abrir carpeta", command=self.open_project).pack(side="right")

    def _build_logs_tab(self, parent: ttk.Frame) -> None:
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Actualizar", command=self.refresh_logs).pack(side="left")
        ttk.Button(actions, text="Abrir archivo", command=self.open_log).pack(side="left", padx=8)
        self.log_text = tk.Text(parent, bg="#08111c", fg="#cbd8e6", insertbackground=self.TEXT, relief="flat", font=("Cascadia Mono", 9), padx=12, pady=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    @staticmethod
    def _toggle_secret(entry: ttk.Entry) -> None:
        entry.configure(show="" if entry.cget("show") else "*")

    def load_configuration(self) -> None:
        values = _read_env()
        defaults = {"DATABASE_PATH": "data/galerazo.sqlite3", "GOOGLE_SHEETS_WORKSHEET_NAME": "Gastos"}
        for key, variable in self.variables.items():
            variable.set(values.get(key, defaults.get(key, "")))

    def save_configuration(self, notify: bool = True) -> bool:
        token = self.variables["TELEGRAM_BOT_TOKEN"].get().strip()
        if not token or token == "replace-me":
            messagebox.showwarning("Configuracion incompleta", "Configura un token valido de Telegram antes de guardar.")
            self.notebook.select(self.config_tab)
            return False
        _write_env({key: variable.get().strip() for key, variable in self.variables.items()})
        if notify:
            messagebox.showinfo("Configuracion", "La configuracion se guardo correctamente.")
        return True

    def start_bot(self) -> None:
        if _running_process_id() is not None:
            self.refresh_status()
            return
        if not self.save_configuration(notify=False):
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.startup_log_offset = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
            log = LOG_PATH.open("a", encoding="utf-8")
            process = subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / "app.py")],
                cwd=PROJECT_ROOT,
                env={**os.environ, **_read_env()},
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            log.close()
            self.starting_process = process
            PID_PATH.write_text(str(process.pid), encoding="ascii")
            self.status_dot.itemconfigure(self.status_circle, fill=self.AMBER)
            self.status_label.configure(text="INICIANDO...")
            self.detail_label.configure(text=f"Validando configuracion y conexion - PID {process.pid}")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.restart_button.configure(state="disabled")
            self.after(2500, lambda: self._check_startup(process))
        except Exception as error:
            messagebox.showerror("No se pudo iniciar", str(error))

    def _check_startup(self, process: subprocess.Popen[str]) -> None:
        if self.starting_process is not process:
            return
        self.starting_process = None
        if process.poll() is None:
            self.refresh_status()
            return

        PID_PATH.unlink(missing_ok=True)
        self.refresh_logs()
        self.refresh_status()
        self.notebook.select(self.logs_tab)
        error = self._startup_error_text()
        messagebox.showerror("El bot no pudo encender", error)

    def _startup_error_text(self) -> str:
        if not LOG_PATH.exists():
            return "El proceso termino durante el inicio y no dejo un mensaje de error."
        with LOG_PATH.open("r", encoding="utf-8", errors="replace") as log:
            log.seek(self.startup_log_offset)
            lines = [line.rstrip() for line in log.readlines() if line.strip()]
        detail = "\n".join(lines[-12:])
        return detail or "El proceso termino durante el inicio y no dejo un mensaje de error."

    def stop_bot(self) -> None:
        pid = _running_process_id()
        if pid is None:
            self.refresh_status()
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                os.kill(pid, 15)
            PID_PATH.unlink(missing_ok=True)
            self.starting_process = None
        except Exception as error:
            messagebox.showerror("No se pudo apagar", str(error))
        self.refresh_status()

    def restart_bot(self) -> None:
        self.stop_bot()
        self.after(350, self.start_bot)

    def refresh_status(self) -> None:
        pid = _running_process_id()
        running = pid is not None
        starting = running and self.starting_process is not None and self.starting_process.pid == pid
        color = self.AMBER if starting else self.GREEN if running else self.RED
        label = "INICIANDO..." if starting else "BOT ENCENDIDO" if running else "BOT APAGADO"
        detail = f"Validando configuracion y conexion - PID {pid}" if starting else f"Proceso local activo - PID {pid}" if running else "No hay ningun proceso del bot activo."
        self.status_dot.itemconfigure(self.status_circle, fill=color)
        self.status_label.configure(text=label)
        self.detail_label.configure(text=detail)
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.restart_button.configure(state="normal" if running and not starting else "disabled")

    def refresh_logs(self) -> None:
        content = "Todavia no hay logs locales."
        if LOG_PATH.exists():
            with LOG_PATH.open("r", encoding="utf-8", errors="replace") as log:
                log.seek(0, 2)
                size = log.tell()
                log.seek(max(0, size - 100_000))
                content = log.read()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", content)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def open_project(self) -> None:
        os.startfile(PROJECT_ROOT)

    def open_log(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOG_PATH.touch(exist_ok=True)
        os.startfile(LOG_PATH)

    def _status_tick(self) -> None:
        self.refresh_status()
        self.after(1500, self._status_tick)


def main() -> None:
    _configure_windows_app_identity()
    instance = SingleInstance(f"control-panel:{PROJECT_ROOT}")
    if not instance.acquire():
        messagebox.showinfo("Galerazo Bot", "El panel de control ya esta abierto.")
        return
    try:
        ControlPanel().mainloop()
    finally:
        instance.release()


def _configure_windows_app_identity() -> None:
    if os.name != "nt":
        return
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
