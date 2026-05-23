import os
import json
import subprocess
import time
import shutil
import threading
from datetime import datetime
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkcalendar import DateEntry
import requests

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────────────────────────
#  AUTO-DETECTION
# ─────────────────────────────────────────────────────────────────

def find_mt5_executables():
    """Escanea ubicaciones comunes buscando terminal64.exe"""
    found = []
    pf_dirs = []
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"):
        d = os.environ.get(env, "")
        if d and d not in pf_dirs:
            pf_dirs.append(d)
    for default in (r"C:\Program Files", r"C:\Program Files (x86)"):
        if default not in pf_dirs:
            pf_dirs.append(default)

    for pf in pf_dirs:
        if not os.path.isdir(pf):
            continue
        try:
            for folder in os.listdir(pf):
                exe = os.path.join(pf, folder, "terminal64.exe")
                if os.path.isfile(exe) and exe not in found:
                    found.append(exe)
        except Exception:
            pass
    return found


def find_mt5_data_paths():
    """Busca carpetas de datos de MT5 en %APPDATA%\\MetaQuotes\\Terminal\\"""
    found = []
    appdata = os.environ.get("APPDATA", "")
    terminal_base = os.path.join(appdata, "MetaQuotes", "Terminal")
    if not os.path.isdir(terminal_base):
        return found
    try:
        for guid in os.listdir(terminal_base):
            path = os.path.join(terminal_base, guid)
            if os.path.isdir(os.path.join(path, "MQL5", "Experts")):
                found.append(path)
    except Exception:
        pass
    return found


# ─────────────────────────────────────────────────────────────────
#  SETTINGS WINDOW
# ─────────────────────────────────────────────────────────────────

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configuración")
        self.geometry("720x580")
        self.resizable(False, False)
        self.configure(fg_color=("#0f0f0f", "#0a0a0a"))
        self.grab_set()

        ctk.CTkLabel(
            self, text="Configuración",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=("#ffffff", "#ffffff")
        ).pack(padx=40, pady=(30, 20), anchor="w")

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=("#1a1a1a", "#141414"),
            segmented_button_fg_color=("#1a1a1a", "#141414"),
            segmented_button_selected_color=("#00d9ff", "#00d9ff"),
            segmented_button_selected_hover_color=("#00b8d4", "#00b8d4"),
            segmented_button_unselected_color=("#252525", "#1f1f1f"),
            segmented_button_unselected_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"),
            corner_radius=12,
        )
        self.tabs.pack(padx=40, fill="both", expand=True)
        self.tabs.add("MT5")
        self.tabs.add("Telegram")
        self.tabs.add("Defaults")

        self._build_mt5_tab()
        self._build_telegram_tab()
        self._build_defaults_tab()

        ctk.CTkButton(
            self, text="Guardar configuración",
            height=48, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#00d9ff", "#00d9ff"),
            hover_color=("#00b8d4", "#00b8d4"),
            text_color=("#000000", "#000000"),
            command=self._save
        ).pack(padx=40, pady=(16, 30), fill="x")

    # ── MT5 Tab ──────────────────────────────────────────────────

    def _build_mt5_tab(self):
        tab = self.tabs.tab("MT5")
        conf = self.parent.conf

        # Executable
        self._lbl(tab, "Ejecutable de MT5  (terminal64.exe)")
        row_exe = ctk.CTkFrame(tab, fg_color="transparent")
        row_exe.pack(fill="x", pady=(0, 4))
        row_exe.columnconfigure(0, weight=1)

        self.entry_exe = self._entry(row_exe, conf.get("mt5_path", ""), "Ruta al terminal64.exe…")
        self.entry_exe.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._small_btn(row_exe, "Browse", self._browse_exe).grid(row=0, column=1, padx=(0, 8))

        self.lbl_exe_ok = ctk.CTkLabel(row_exe, text="", width=22)
        self.lbl_exe_ok.grid(row=0, column=2)
        self._check_exe()

        # Auto-detected executables
        exes = find_mt5_executables()
        if exes:
            self._lbl(tab, "Instalaciones detectadas automáticamente")
            self.combo_exes = self._combo(tab, exes)
            cur = conf.get("mt5_path", "")
            self.combo_exes.set(cur if cur in exes else exes[0])
            self.combo_exes.configure(command=lambda v: (
                self.entry_exe.delete(0, "end"),
                self.entry_exe.insert(0, v),
                self._check_exe()
            ))
            self.combo_exes.pack(fill="x", pady=(0, 4))

        # Data folder
        self._lbl(tab, "Carpeta de datos de MT5  (AppData/MetaQuotes/Terminal/GUID)")
        row_data = ctk.CTkFrame(tab, fg_color="transparent")
        row_data.pack(fill="x", pady=(0, 4))
        row_data.columnconfigure(0, weight=1)

        self.entry_data = self._entry(row_data, conf.get("mt5_data_path", ""), "Ruta a la carpeta Terminal/GUID…")
        self.entry_data.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._small_btn(row_data, "Browse", self._browse_data).grid(row=0, column=1, padx=(0, 8))

        self.lbl_data_ok = ctk.CTkLabel(row_data, text="", width=22)
        self.lbl_data_ok.grid(row=0, column=2)
        self._check_data()

        # Auto-detected data paths
        data_paths = find_mt5_data_paths()
        if data_paths:
            self._lbl(tab, "Carpetas de datos detectadas")
            self.combo_data = self._combo(tab, data_paths)
            cur = conf.get("mt5_data_path", "")
            self.combo_data.set(cur if cur in data_paths else data_paths[0])
            self.combo_data.configure(command=lambda v: (
                self.entry_data.delete(0, "end"),
                self.entry_data.insert(0, v),
                self._check_data()
            ))
            self.combo_data.pack(fill="x", pady=(0, 4))

    def _lbl(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#666666", "#666666")
        ).pack(anchor="w", pady=(14, 4))

    def _entry(self, parent, value, placeholder):
        e = ctk.CTkEntry(
            parent, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=12),
            placeholder_text=placeholder
        )
        e.insert(0, value)
        return e

    def _small_btn(self, parent, text, cmd):
        return ctk.CTkButton(
            parent, text=text, width=80, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#00d9ff", "#00d9ff"), font=ctk.CTkFont(size=12),
            command=cmd
        )

    def _combo(self, parent, values):
        return ctk.CTkComboBox(
            parent, values=values, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=11)
        )

    def _browse_exe(self):
        path = filedialog.askopenfilename(
            title="Seleccionar terminal64.exe",
            filetypes=[("MT5 executable", "terminal64.exe"), ("Ejecutables", "*.exe")]
        )
        if path:
            self.entry_exe.delete(0, "end")
            self.entry_exe.insert(0, path.replace("/", "\\"))
            self._check_exe()

    def _browse_data(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de datos de MT5")
        if path:
            self.entry_data.delete(0, "end")
            self.entry_data.insert(0, path.replace("/", "\\"))
            self._check_data()

    def _check_exe(self):
        ok = os.path.isfile(self.entry_exe.get())
        self.lbl_exe_ok.configure(
            text="✓" if ok else "✗",
            text_color=("#34d399" if ok else "#fb5a6f", "#34d399" if ok else "#fb5a6f")
        )

    def _check_data(self):
        ok = os.path.isdir(os.path.join(self.entry_data.get(), "MQL5", "Experts"))
        self.lbl_data_ok.configure(
            text="✓" if ok else "✗",
            text_color=("#34d399" if ok else "#fb5a6f", "#34d399" if ok else "#fb5a6f")
        )

    # ── Telegram Tab ─────────────────────────────────────────────

    def _build_telegram_tab(self):
        tab = self.tabs.tab("Telegram")
        tg = self.parent.conf.get("telegram", {})

        self.tg_enabled = ctk.BooleanVar(value=tg.get("enabled", False))
        ctk.CTkSwitch(
            tab, text="Activar notificaciones de Telegram",
            variable=self.tg_enabled,
            font=ctk.CTkFont(size=13),
            progress_color=("#00d9ff", "#00d9ff"),
            text_color=("#ffffff", "#ffffff")
        ).pack(anchor="w", pady=(18, 20))

        self._lbl(tab, "Bot Token")
        self.entry_token = ctk.CTkEntry(
            tab, height=42, corner_radius=8, show="•",
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=12),
            placeholder_text="1234567890:AABBCCddeeff…"
        )
        self.entry_token.pack(fill="x", pady=(0, 14))
        self.entry_token.insert(0, tg.get("bot_token", ""))

        self._lbl(tab, "Chat ID")
        self.entry_chat = ctk.CTkEntry(
            tab, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=12),
            placeholder_text="Tu chat ID de Telegram…"
        )
        self.entry_chat.pack(fill="x", pady=(0, 20))
        self.entry_chat.insert(0, tg.get("chat_id", ""))

        self.btn_test = ctk.CTkButton(
            tab, text="Probar conexión",
            height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#00d9ff", "#00d9ff"), font=ctk.CTkFont(size=13),
            command=self._test_telegram
        )
        self.btn_test.pack(fill="x")

        self.lbl_tg_result = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=12))
        self.lbl_tg_result.pack(pady=(10, 0))

    def _test_telegram(self):
        token = self.entry_token.get().strip()
        chat_id = self.entry_chat.get().strip()
        if not token or not chat_id:
            self.lbl_tg_result.configure(
                text="⚠  Completa el token y el Chat ID primero",
                text_color=("#fbbf24", "#fbbf24")
            )
            return
        self.btn_test.configure(state="disabled", text="Enviando…")

        def _send():
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": "✅ MT5 Backtest Pro — conexión verificada correctamente."},
                    timeout=10
                )
                ok = r.status_code == 200
                self.lbl_tg_result.configure(
                    text="✓  Mensaje enviado correctamente" if ok else f"✗  Error {r.status_code}",
                    text_color=("#34d399" if ok else "#fb5a6f", "#34d399" if ok else "#fb5a6f")
                )
            except Exception as e:
                self.lbl_tg_result.configure(text=f"✗  {e}", text_color=("#fb5a6f", "#fb5a6f"))
            finally:
                self.btn_test.configure(state="normal", text="Probar conexión")

        threading.Thread(target=_send, daemon=True).start()

    # ── Defaults Tab ─────────────────────────────────────────────

    def _build_defaults_tab(self):
        tab = self.tabs.tab("Defaults")
        cs = self.parent.conf.get("common_settings", {})

        self._lbl(tab, "Depósito por defecto (USD)")
        self.entry_deposit = ctk.CTkEntry(
            tab, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.entry_deposit.pack(fill="x", pady=(0, 16))
        self.entry_deposit.insert(0, str(cs.get("deposit", 100000)))

        self._lbl(tab, "Apalancamiento por defecto")
        self.entry_leverage = ctk.CTkEntry(
            tab, height=42, corner_radius=8,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.entry_leverage.pack(fill="x", pady=(0, 16))
        self.entry_leverage.insert(0, str(cs.get("leverage", "1:100")))

    # ── Save ─────────────────────────────────────────────────────

    def _save(self):
        conf = self.parent.conf
        conf["mt5_path"]      = self.entry_exe.get().strip()
        conf["mt5_data_path"] = self.entry_data.get().strip()
        conf["telegram"]["enabled"]   = self.tg_enabled.get()
        conf["telegram"]["bot_token"] = self.entry_token.get().strip()
        conf["telegram"]["chat_id"]   = self.entry_chat.get().strip()
        try:
            conf["common_settings"]["deposit"] = int(self.entry_deposit.get())
        except ValueError:
            pass
        conf["common_settings"]["leverage"] = self.entry_leverage.get().strip()
        self.parent.save_config()
        self.parent.on_settings_saved()
        self.destroy()


# ─────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────

class BacktestGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MT5 Backtest Pro")
        self.geometry("1100x920")
        self.configure(fg_color=("#0f0f0f", "#0a0a0a"))

        self.load_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()        # row 0
        self._build_setup_banner()  # row 1 (oculto si está configurado)
        self._build_config_panel()  # row 2
        self._build_log()           # row 3
        self._build_run_button()    # row 4

        self._update_banner()

    # ── HEADER ───────────────────────────────────────────────────

    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, padx=40, pady=(36, 16), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left, text="MT5 Backtest Pro",
            font=ctk.CTkFont(size=34, weight="bold"),
            text_color=("#ffffff", "#ffffff")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left, text="Automated backtesting system",
            font=ctk.CTkFont(size=13),
            text_color=("#555555", "#555555")
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        right = ctk.CTkFrame(frame, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")

        self.lbl_config_status = ctk.CTkLabel(
            right, text="",
            font=ctk.CTkFont(size=12),
            text_color=("#666666", "#666666")
        )
        self.lbl_config_status.grid(row=0, column=0, padx=(0, 16))

        ctk.CTkButton(
            right, text="⚙  Configuración",
            height=40, corner_radius=10,
            fg_color=("#1a1a1a", "#141414"),
            hover_color=("#252525", "#1f1f1f"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#00d9ff", "#00d9ff"),
            font=ctk.CTkFont(size=13),
            command=self._open_settings
        ).grid(row=0, column=1)

    # ── SETUP BANNER ─────────────────────────────────────────────

    def _build_setup_banner(self):
        self.frame_banner = ctk.CTkFrame(
            self,
            fg_color=("#1a0e0e", "#140a0a"),
            corner_radius=12,
            border_width=1,
            border_color=("#fb5a6f", "#e02d4a")
        )
        self.frame_banner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.frame_banner,
            text="⚠  Configuración incompleta — MT5 no está configurado correctamente.",
            font=ctk.CTkFont(size=13),
            text_color=("#fb5a6f", "#fb5a6f")
        ).grid(row=0, column=0, padx=20, pady=14, sticky="w")

        ctk.CTkButton(
            self.frame_banner, text="Configurar ahora →",
            height=34, corner_radius=8,
            fg_color="transparent", hover_color=("#2a1414", "#201010"),
            border_width=1, border_color=("#fb5a6f", "#e02d4a"),
            text_color=("#fb5a6f", "#fb5a6f"), font=ctk.CTkFont(size=12),
            command=self._open_settings
        ).grid(row=0, column=1, padx=(0, 20), pady=14)

    def _update_banner(self):
        if self._is_configured():
            self.frame_banner.grid_remove()
            self.lbl_config_status.configure(
                text="●  MT5 configurado",
                text_color=("#34d399", "#34d399")
            )
        else:
            self.frame_banner.grid(row=1, column=0, padx=40, pady=(0, 16), sticky="ew")
            self.lbl_config_status.configure(
                text="●  Sin configurar",
                text_color=("#fb5a6f", "#fb5a6f")
            )
        # Refresh folder list
        self.carpetas_disponibles = self.detectar_carpetas()
        if self.carpetas_disponibles:
            self.combo_folder.configure(values=self.carpetas_disponibles)
            cur = self.conf.get("ea_folder", "")
            self.combo_folder.set(cur if cur in self.carpetas_disponibles else self.carpetas_disponibles[0])
        else:
            self.combo_folder.configure(values=["— no se encontraron carpetas —"])
            self.combo_folder.set("— no se encontraron carpetas —")

    def _is_configured(self):
        exe  = self.conf.get("mt5_path", "")
        data = self.conf.get("mt5_data_path", "")
        return (
            os.path.isfile(exe) and
            os.path.isdir(os.path.join(data, "MQL5", "Experts"))
        )

    # ── CONFIG PANEL ─────────────────────────────────────────────

    def _build_config_panel(self):
        frame = ctk.CTkFrame(self, fg_color=("#1a1a1a", "#141414"), corner_radius=16)
        frame.grid(row=2, column=0, padx=40, pady=(0, 16), sticky="ew")
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        # EA Folder
        self._slbl(frame, "Expert Advisor Folder", 0, 0)
        row_folder = ctk.CTkFrame(frame, fg_color="transparent")
        row_folder.grid(row=1, column=0, padx=25, pady=(0, 28), sticky="ew")
        row_folder.grid_columnconfigure(0, weight=1)

        self.carpetas_disponibles = self.detectar_carpetas()
        self.combo_folder = ctk.CTkComboBox(
            row_folder,
            values=self.carpetas_disponibles if self.carpetas_disponibles else ["— no se encontraron carpetas —"],
            height=46, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        ea = self.conf.get("ea_folder", "")
        self.combo_folder.set(ea if ea in self.carpetas_disponibles else (self.carpetas_disponibles[0] if self.carpetas_disponibles else "— no se encontraron carpetas —"))
        self.combo_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row_folder, text="↻", width=46, height=46, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            font=ctk.CTkFont(size=20), text_color=("#666666", "#666666"),
            command=self.refrescar_carpetas
        ).grid(row=0, column=1)

        # Symbol
        self._slbl(frame, "Symbol", 0, 1)
        self.combo_symbol = ctk.CTkComboBox(
            frame,
            values=["EURUSD", "GBPUSD", "GDAXI", "NDX", "USDCHF", "USDJPY", "WS30", "XAUUSD", "XTIUSD"],
            height=46, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.combo_symbol.set(self.conf["common_settings"].get("symbol", "XAUUSD"))
        self.combo_symbol.grid(row=1, column=1, padx=25, pady=(0, 28), sticky="ew")

        # Timeframe
        self._slbl(frame, "Timeframe", 0, 2)
        self.combo_period = ctk.CTkComboBox(
            frame,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"],
            height=46, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.combo_period.set(self.conf["common_settings"].get("period", "H1"))
        self.combo_period.grid(row=1, column=2, padx=25, pady=(0, 28), sticky="ew")

        sep = ctk.CTkFrame(frame, height=1, fg_color=("#252525", "#1f1f1f"))
        sep.grid(row=2, column=0, columnspan=3, padx=25, pady=(0, 28), sticky="ew")

        # Dates
        self._slbl(frame, "Start Date", 3, 0)
        fr_from = ctk.CTkFrame(frame, fg_color=("#252525", "#1f1f1f"), corner_radius=10, border_width=1, border_color=("#2a2a2a", "#252525"))
        fr_from.grid(row=4, column=0, padx=25, pady=(0, 28), sticky="ew")
        self.date_from = DateEntry(fr_from, width=30, background="#1f1f1f", foreground="white", borderwidth=0, font=("Arial", 11), date_pattern="yyyy.mm.dd", year=2020, month=1, day=1)
        self.date_from.pack(padx=12, pady=12, fill="x")

        self._slbl(frame, "End Date", 3, 1)
        fr_to = ctk.CTkFrame(frame, fg_color=("#252525", "#1f1f1f"), corner_radius=10, border_width=1, border_color=("#2a2a2a", "#252525"))
        fr_to.grid(row=4, column=1, padx=25, pady=(0, 28), sticky="ew")
        self.date_to = DateEntry(fr_to, width=30, background="#1f1f1f", foreground="white", borderwidth=0, font=("Arial", 11), date_pattern="yyyy.mm.dd", year=2025, month=12, day=28)
        self.date_to.pack(padx=12, pady=12, fill="x")

        ctk.CTkButton(
            frame, text="Use Default Range",
            height=46, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#666666", "#666666"), font=ctk.CTkFont(size=12),
            command=self.set_default_dates
        ).grid(row=4, column=2, padx=25, pady=(0, 28), sticky="ew")

    def _slbl(self, parent, text, row, col):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#666666", "#666666")
        ).grid(row=row, column=col, padx=25, pady=(28, 8), sticky="w")

    # ── LOG ──────────────────────────────────────────────────────

    def _build_log(self):
        frame = ctk.CTkFrame(self, fg_color=("#1a1a1a", "#141414"), corner_radius=16)
        frame.grid(row=3, column=0, padx=40, pady=(0, 16), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#ffffff", "#ffffff")
        ).grid(row=0, column=0, padx=25, pady=(22, 12), sticky="w")

        self.logbox = ctk.CTkTextbox(
            frame, font=("Courier", 11),
            fg_color=("#0f0f0f", "#0a0a0a"),
            text_color=("#00d9ff", "#00d9ff"),
            corner_radius=10, border_width=0
        )
        self.logbox.grid(row=1, column=0, padx=25, pady=(0, 22), sticky="nsew")
        self.logbox.configure(state="disabled")

    # ── RUN BUTTON ───────────────────────────────────────────────

    def _build_run_button(self):
        self.btn = ctk.CTkButton(
            self, text="Start Backtest",
            height=54, corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#00d9ff", "#00d9ff"),
            hover_color=("#00b8d4", "#00b8d4"),
            text_color=("#000000", "#000000"),
            command=self.start_thread
        )
        self.btn.grid(row=4, column=0, padx=40, pady=(0, 36), sticky="ew")

    # ── HELPERS ──────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self)

    def on_settings_saved(self):
        self._update_banner()
        self.log("✓ Configuración guardada correctamente")

    def set_default_dates(self):
        self.date_from.set_date(datetime(2020, 1, 1))
        self.date_to.set_date(datetime(2025, 12, 28))
        self.log("Default date range applied: 2020.01.01 - 2025.12.28")

    def detectar_carpetas(self):
        try:
            ruta_experts = os.path.join(self.conf.get("mt5_data_path", ""), "MQL5", "Experts")
            if not os.path.isdir(ruta_experts):
                return []
            carpetas = []
            for root, dirs, files in os.walk(ruta_experts):
                if any(f.endswith(".ex5") for f in files):
                    rel = os.path.relpath(root, ruta_experts)
                    if rel != ".":
                        carpetas.append(rel)
            return sorted(carpetas)
        except Exception:
            return []

    def refrescar_carpetas(self):
        self.carpetas_disponibles = self.detectar_carpetas()
        if self.carpetas_disponibles:
            self.combo_folder.configure(values=self.carpetas_disponibles)
            self.combo_folder.set(self.carpetas_disponibles[0])
            self.log("Folders refreshed")
        else:
            self.combo_folder.configure(values=["— no se encontraron carpetas —"])
            self.combo_folder.set("— no se encontraron carpetas —")
            self.log("No .ex5 folders found")

    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                self.conf = json.load(f)
            self.conf.setdefault("mt5_data_path", "")
            self.conf.setdefault("telegram", {"enabled": False, "bot_token": "", "chat_id": ""})
        except Exception:
            self.conf = {
                "mt5_path": "", "mt5_data_path": "", "ea_folder": "",
                "common_settings": {
                    "deposit": 100000, "currency": "USD",
                    "leverage": "1:100", "symbol": "XAUUSD", "period": "H1"
                },
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""}
            }

    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.conf, f, indent=2, ensure_ascii=False)

    def log(self, text):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", f"{time.strftime('%H:%M:%S')} → {text}\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def send_telegram_message(self, message):
        try:
            tg = self.conf.get("telegram", {})
            if not tg.get("enabled") or not tg.get("bot_token") or not tg.get("chat_id"):
                return False
            r = requests.post(
                f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                data={"chat_id": tg["chat_id"], "text": message, "parse_mode": "HTML"},
                timeout=10
            )
            return r.status_code == 200
        except Exception:
            return False

    # ── RUN BACKTESTS ────────────────────────────────────────────

    def start_thread(self):
        if not self._is_configured():
            messagebox.showwarning(
                "Sin configurar",
                "Configura la ruta de MT5 antes de correr backtests.\nUsa el botón ⚙ Configuración."
            )
            return
        threading.Thread(target=self.run_backtests, daemon=True).start()

    def run_backtests(self):
        self.btn.configure(
            state="disabled", text="Processing…",
            fg_color=("#2a2a2a", "#252525"), text_color=("#666666", "#666666")
        )
        start_time = time.time()
        exitosos = fallidos = 0

        try:
            carpeta_final = os.path.abspath("reports")
            os.makedirs(carpeta_final, exist_ok=True)

            ruta_mt5    = self.conf.get("mt5_data_path", "")
            ruta_experts = os.path.join(ruta_mt5, "MQL5", "Experts", self.combo_folder.get())
            ruta_files   = os.path.join(ruta_mt5, "MQL5", "Files")

            if not os.path.exists(ruta_experts):
                self.log(f"Error: carpeta no encontrada → {ruta_experts}")
                return

            expertos = [f for f in os.listdir(ruta_experts) if f.endswith(".ex5")]
            total = len(expertos)
            self.log(f"Found {total} Expert Advisors")
            self.log("─" * 50)

            self.send_telegram_message(
                f"🚀 <b>MT5 Backtest Started</b>\n\n"
                f"📊 Total EAs: {total}\n"
                f"💱 Symbol: {self.combo_symbol.get()}\n"
                f"⏰ Timeframe: {self.combo_period.get()}\n"
                f"📅 Period: {self.date_from.get_date().strftime('%Y.%m.%d')} - {self.date_to.get_date().strftime('%Y.%m.%d')}"
            )

            for idx, ea in enumerate(expertos, 1):
                self.log(f"[{idx}/{total}] Testing → {ea}")
                nombre_temp = "reporte.html"
                for r in [os.path.join(ruta_files, nombre_temp), os.path.join(ruta_mt5, nombre_temp)]:
                    if os.path.exists(r):
                        os.remove(r)

                ini_content = (
                    "[Tester]\n"
                    f'Expert="{self.combo_folder.get()}\\{ea}"\n'
                    f"Symbol={self.combo_symbol.get()}\n"
                    f"Period={self.combo_period.get()}\n"
                    f"Deposit={self.conf['common_settings']['deposit']}\n"
                    f"Leverage={self.conf['common_settings']['leverage']}\n"
                    "Model=1\n"
                    f"FromDate={self.date_from.get_date().strftime('%Y.%m.%d')}\n"
                    f"ToDate={self.date_to.get_date().strftime('%Y.%m.%d')}\n"
                    f"Report={nombre_temp}\nReplaceReport=1\nShutdownTerminal=1\nVisual=0\n"
                )

                ini_path = os.path.abspath("config_batch.ini")
                with open(ini_path, "w", encoding="utf-16") as f:
                    f.write(ini_content)

                subprocess.run([self.conf["mt5_path"], f"/config:{ini_path}"], capture_output=True)

                encontrado = False
                for _ in range(15):
                    time.sleep(1)
                    for origen in [os.path.join(ruta_files, nombre_temp), os.path.join(ruta_mt5, nombre_temp)]:
                        if os.path.exists(origen):
                            destino = os.path.join(carpeta_final, ea.replace(".ex5", ".html"))
                            shutil.move(origen, destino)
                            self.log(f"  ✓ {ea.replace('.ex5', '.html')}")
                            exitosos += 1
                            encontrado = True
                            break
                    if encontrado:
                        break

                if not encontrado:
                    self.log("  ✗ Report not generated")
                    fallidos += 1

            tiempo_total = int(time.time() - start_time)
            mins, secs = tiempo_total // 60, tiempo_total % 60
            self.log("─" * 50)
            self.log(f"Completed → {exitosos} OK, {fallidos} failed — {mins}m {secs}s")

            self.send_telegram_message(
                f"{'✅' if fallidos == 0 else '⚠️'} <b>Backtest Completed!</b>\n\n"
                f"✅ Successful: {exitosos}\n❌ Failed: {fallidos}\n"
                f"⏱ Time: {mins}m {secs}s\n"
                f"💱 {self.combo_symbol.get()} {self.combo_period.get()}"
            )
            messagebox.showinfo("Completado", f"{exitosos} EAs procesados · {fallidos} fallidos")

        except Exception as e:
            self.log(f"Error crítico → {e}")
            self.send_telegram_message(f"❌ <b>Error en backtest</b>\n{e}\n✅ {exitosos}  ❌ {fallidos}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn.configure(
                state="normal", text="Start Backtest",
                fg_color=("#00d9ff", "#00d9ff"), text_color=("#000000", "#000000")
            )


if __name__ == "__main__":
    app = BacktestGUI()
    app.mainloop()
