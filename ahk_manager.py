import tkinter as tk
from tkinter import font as tkfont
import subprocess
import threading
import os
import shutil
import tempfile

from config import (
    CURRENT_VERSION,
    load_theme, load_stats, save_stats, load_favs, save_favs,
    load_keybinds, save_keybinds, clear_session,
    fetch_remote_users, find_autohotkey, resource_path,
)
from scripts_loader import get_scripts_for_server
from toggle_switch import ToggleSwitch
from theme_editor import ThemeEditor
from updater import check_for_update, show_update_prompt


class AHKManager(tk.Tk):
    def __init__(self, current_user="", server="Prison", allowed_scripts=None):
        super().__init__()
        self.title(f"Nebula — {server}")
        self.resizable(True, True)
        self._current_user    = current_user
        self._is_admin        = (current_user == "Physica")
        self._server          = server
        # allowed_scripts: None=all, []=none, [list]=filtered filenames
        self._allowed_scripts = allowed_scripts

        try:
            self.iconbitmap(resource_path("nebula.ico"))
        except Exception:
            pass

        self.ahk_path = find_autohotkey()
        self.tmp_dir  = tempfile.mkdtemp(prefix="ahkman_")
        self.procs    = {}
        self._theme   = load_theme()
        self._widgets = []
        self._stats   = load_stats()
        self._favs    = load_favs()
        self._keybinds = load_keybinds()
        self._opacity  = 1.0

        self._build_fonts()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

        threading.Thread(target=self._bg_check_update, daemon=True).start()

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _t(self, key):
        return self._theme[key]

    def _build_fonts(self):
        self.font_title  = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self.font_name   = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.font_file   = tkfont.Font(family="Segoe UI", size=8)
        self.font_status = tkfont.Font(family="Segoe UI", size=8,  weight="bold")
        self.font_badge  = tkfont.Font(family="Segoe UI", size=7,  weight="bold")

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        t = self._theme
        self.configure(bg=t["bg"])

        # Header
        self._header = tk.Frame(self, bg=t["bg"], padx=28, pady=14)
        self._header.pack(fill="x")

        self._title_lbl = tk.Label(
            self._header, text=f"⬡ Nebula  v{CURRENT_VERSION}",
            font=tkfont.Font(family="Segoe Script", size=15, weight="bold"),
            bg=t["bg"], fg=t["accent"])
        self._title_lbl.pack(side="left")

        # Right-side header buttons
        self._theme_btn = tk.Label(
            self._header, text="⚙ Theme", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._theme_btn.pack(side="right")
        self._theme_btn.bind("<Button-1>", lambda e: self._open_theme_editor())

        self._logout_btn = tk.Label(
            self._header, text="⏏ Logout", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent2"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._logout_btn.pack(side="right", padx=(0, 8))
        self._logout_btn.bind("<Button-1>", lambda e: self._logout())

        self._help_btn = tk.Label(
            self._header, text="? Help", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._help_btn.pack(side="right", padx=(0, 8))
        self._help_btn.bind("<Button-1>", lambda e: self._open_hotkey_help())

        self._kb_btn = tk.Label(
            self._header, text="⌨ Keybinds", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._kb_btn.pack(side="right", padx=(0, 8))
        self._kb_btn.bind("<Button-1>", lambda e: self._open_keybind_editor())

        self._blank_btn = tk.Label(
            self._header, text="⬜ Blank", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._blank_btn.pack(side="right", padx=(0, 8))
        self._blank_btn.bind("<Button-1>", lambda e: self._open_blank_window())

        self._server_btn = tk.Label(
            self._header, text=f"🌐 {self._server}", font=self.font_badge,
            bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
            cursor="hand2", relief="flat",
            highlightbackground=t["border"], highlightthickness=1)
        self._server_btn.pack(side="right", padx=(0, 8))
        self._server_btn.bind("<Button-1>", lambda e: self._change_server())

        if self._is_admin:
            self._admin_btn = tk.Label(
                self._header, text="👥 Users", font=self.font_badge,
                bg=t["card_bg"], fg=t["running"], padx=10, pady=5,
                cursor="hand2", relief="flat",
                highlightbackground=t["border"], highlightthickness=1)
            self._admin_btn.pack(side="right", padx=(0, 8))
            self._admin_btn.bind("<Button-1>", lambda e: self._open_admin_panel())

        if not self.ahk_path:
            self._no_ahk_lbl = tk.Label(
                self._header, text="⚠  AutoHotkey not found",
                font=self.font_badge, bg=t["bg"], fg=t["accent2"])
            self._no_ahk_lbl.pack(side="right", padx=12)

        self._div1 = tk.Frame(self, bg=t["border"], height=1)
        self._div1.pack(fill="x", padx=28)

        # Search + Stop All bar
        self._toolbar = tk.Frame(self, bg=t["bg"], padx=28, pady=8)
        self._toolbar.pack(fill="x")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_cards())
        self._search_entry = tk.Entry(
            self._toolbar, textvariable=self._search_var,
            font=self.font_file, bg=t["card_bg"],
            fg=t["text"], insertbackground=t["accent"],
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["accent"])
        self._search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))

        self._search_placeholder = "Search scripts..."
        self._search_entry.insert(0, self._search_placeholder)
        self._search_entry.config(fg=t["subtext"])
        self._search_entry.bind("<FocusIn>",  self._search_focus_in)
        self._search_entry.bind("<FocusOut>", self._search_focus_out)

        self._stopall_btn = tk.Label(
            self._toolbar, text="⏹ Stop All", font=self.font_badge,
            bg=t["accent2"], fg="#ffffff", padx=12, pady=6,
            cursor="hand2", relief="flat")
        self._stopall_btn.pack(side="right")
        self._stopall_btn.bind("<Button-1>", lambda e: self._stop_all())

        # Scrollable script area
        self._outer = tk.Frame(self, bg=t["bg"])
        self._outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._outer, bg=t["bg"], highlightthickness=0, bd=0)
        self._scrollbar = tk.Scrollbar(self._outer, orient="vertical",
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._container = tk.Frame(self._canvas, bg=t["bg"], padx=20, pady=16)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._container, anchor="nw")

        self._card_refs = []
        visible = get_scripts_for_server(self._server)
        sorted_scripts = sorted(
            visible, key=lambda s: (0 if s["filename"] in self._favs else 1))

        for info in sorted_scripts:
            card = self._make_card(self._container, info)
            card["frame"].pack(fill="x", pady=6, padx=8)
            self._card_refs.append(card)

        if not sorted_scripts:
            tk.Label(self._container,
                     text="No scripts available for this server.",
                     font=self.font_file, bg=t["bg"], fg=t["subtext"]).pack(pady=40)

        def on_configure(event):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfig(self._canvas_win, width=self._canvas.winfo_width())

        self._container.bind("<Configure>", on_configure)
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._canvas_win, width=e.width))

        self._last_scroll = 0

        def _throttled_scroll(e):
            import time
            now = time.time()
            if now - self._last_scroll < 0.03:
                return
            self._last_scroll = now
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        self._canvas.bind_all("<MouseWheel>", _throttled_scroll)
        self._canvas.configure(height=420)

        self._div2 = tk.Frame(self, bg=t["border"], height=1)
        self._div2.pack(fill="x", padx=28)

        # Footer with opacity slider
        self._footer_frame = tk.Frame(self, bg=t["bg"])
        self._footer_frame.pack(fill="x", padx=28, pady=4)

        self._footer_lbl = tk.Label(
            self._footer_frame,
            text="scripts run from temp dir  ·  close window to stop all",
            font=self.font_badge, bg=t["bg"], fg=t["subtext"])
        self._footer_lbl.pack(side="left")

        opacity_frame = tk.Frame(self._footer_frame, bg=t["bg"])
        opacity_frame.pack(side="right")
        tk.Label(opacity_frame, text="Opacity", font=self.font_badge,
                 bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=(0, 6))
        self._opacity_slider = tk.Scale(
            opacity_frame, from_=30, to=100, orient="horizontal", length=100,
            command=self._set_opacity,
            bg=t["bg"], fg=t["subtext"], troughcolor=t["card_bg"],
            highlightthickness=0, bd=0, showvalue=False, sliderlength=14)
        self._opacity_slider.set(100)
        self._opacity_slider.pack(side="left")

    # ── Script card ───────────────────────────────────────────────────────────
    def _make_card(self, parent, info):
        t  = self._theme
        fn = info["filename"]
        is_fav = fn in self._favs
        stats  = self._stats.get(fn, {"runs": 0, "last": "never"})

        outer = tk.Frame(parent, bg=t["card_bg"],
                         highlightbackground=t["border"], highlightthickness=1)
        inner = tk.Frame(outer, bg=t["card_bg"], padx=18, pady=12)
        inner.pack(fill="x")

        def _dim_color(hex_col, factor=0.4):
            hex_col = hex_col.lstrip("#")
            r, g, b = int(hex_col[0:2], 16), int(hex_col[2:4], 16), int(hex_col[4:6], 16)
            return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

        glow_color = t["accent"]

        def on_enter(e):
            outer.config(highlightbackground=glow_color, highlightthickness=2)

        def on_leave(e):
            outer.config(highlightbackground=t["border"], highlightthickness=1)

        outer.bind("<Enter>", on_enter)
        outer.bind("<Leave>", on_leave)

        # Favourite star
        star_char = "★" if is_fav else "☆"
        star_lbl = tk.Label(inner, text=star_char,
                             font=tkfont.Font(family="Segoe UI", size=16),
                             bg=t["card_bg"],
                             fg=t["accent"] if is_fav else t["subtext"],
                             cursor="hand2")
        star_lbl.pack(side="left", padx=(0, 8))
        star_lbl.bind("<Button-1>", lambda e, f=fn, sl=star_lbl: self._toggle_fav(f, sl))

        left = tk.Frame(inner, bg=t["card_bg"])
        left.pack(side="left", fill="x", expand=True)

        name_lbl = tk.Label(left, text=info["display_name"], font=self.font_name,
                             bg=t["card_bg"], fg=t["text"], anchor="w")
        name_lbl.pack(anchor="w")

        # Info button
        desc = info.get("description", "")
        if desc:
            info_btn = tk.Label(left, text="?", font=self.font_badge,
                                 bg=t["card_bg"], fg=t["accent"], cursor="hand2",
                                 width=2, relief="flat",
                                 highlightbackground=t["border"], highlightthickness=1)
            info_btn.place(in_=name_lbl, relx=1.0, x=4, rely=0, anchor="nw")

            def show_info(e, d=desc, n=info["display_name"]):
                win = tk.Toplevel(self)
                win.title(n)
                win.resizable(False, False)
                win.configure(bg=self._t("bg"))
                win.grab_set()
                tk.Label(win, text=n, font=self.font_name,
                          bg=self._t("bg"), fg=self._t("accent"), pady=12).pack()
                tk.Frame(win, bg=self._t("border"), height=1).pack(fill="x", padx=20)
                tk.Label(win, text=d, font=self.font_file,
                          bg=self._t("bg"), fg=self._t("text"),
                          wraplength=320, justify="left", padx=24, pady=16).pack()
                tk.Frame(win, bg=self._t("border"), height=1).pack(fill="x", padx=20)
                close = tk.Label(win, text="Close", font=self.font_badge,
                                  bg=self._t("card_bg"), fg=self._t("accent2"),
                                  padx=14, pady=7, cursor="hand2",
                                  highlightbackground=self._t("border"), highlightthickness=1)
                close.pack(pady=10)
                close.bind("<Button-1>", lambda e: win.destroy())
                win.update_idletasks()
                px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
                py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
                win.geometry(f"+{px}+{py}")

            info_btn.bind("<Button-1>", show_info)

        file_lbl = tk.Label(left, text=info["filename"], font=self.font_file,
                             bg=t["card_bg"], fg=t["subtext"], anchor="w")
        file_lbl.pack(anchor="w", pady=(1, 0))

        stats_text = f"runs: {stats['runs']}  ·  last: {stats['last']}"
        stats_lbl  = tk.Label(left, text=stats_text, font=self.font_file,
                               bg=t["card_bg"], fg=t["subtext"], anchor="w")
        stats_lbl.pack(anchor="w", pady=(1, 0))

        right = tk.Frame(inner, bg=t["card_bg"])
        right.pack(side="right", padx=(12, 0))

        sv = tk.StringVar(value="STOPPED")
        sl = tk.Label(right, textvariable=sv, font=self.font_status,
                      bg=t["card_bg"], fg=t["stopped"], width=9, anchor="e")
        sl.pack(anchor="e", pady=(0, 4))

        timer_var = tk.StringVar(value="")
        timer_lbl = tk.Label(right, textvariable=timer_var, font=self.font_file,
                              bg=t["card_bg"], fg=t["subtext"], anchor="e")
        timer_lbl.pack(anchor="e", pady=(0, 4))

        tog = ToggleSwitch(right, theme=t,
                           callback=lambda state, i=info, s=sv, l=sl, tg=None:
                               self._toggle(state, i, s, l, tg))
        tog._callback = lambda state, i=info, s=sv, l=sl, tg=tog: self._toggle(state, i, s, l, tg)
        tog.pack(anchor="e")

        return {
            "frame": outer, "inner": inner, "left": left, "right": right,
            "name_lbl": name_lbl, "file_lbl": file_lbl, "stats_lbl": stats_lbl,
            "star_lbl": star_lbl,
            "status_lbl": sl, "status_var": sv, "toggle": tog,
            "timer_var": timer_var, "timer_lbl": timer_lbl,
            "info": info,
            "on_enter": on_enter, "on_leave": on_leave,
        }

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _open_theme_editor(self):
        ThemeEditor(self, self._theme, self._apply_theme)

    def _apply_theme(self, new_theme):
        self._theme = new_theme
        t = new_theme

        self.configure(bg=t["bg"])
        self._header.config(bg=t["bg"])
        self._title_lbl.config(bg=t["bg"], fg=t["accent"])
        self._theme_btn.config(bg=t["card_bg"], fg=t["accent"],
                                highlightbackground=t["border"])
        self._logout_btn.config(bg=t["card_bg"], fg=t["accent2"],
                                 highlightbackground=t["border"])
        self._help_btn.config(bg=t["card_bg"], fg=t["accent"],
                               highlightbackground=t["border"])
        self._kb_btn.config(bg=t["card_bg"], fg=t["accent"],
                             highlightbackground=t["border"])
        self._blank_btn.config(bg=t["card_bg"], fg=t["accent"],
                                highlightbackground=t["border"])
        self._server_btn.config(bg=t["card_bg"], fg=t["accent"],
                                 highlightbackground=t["border"])
        if self._is_admin and hasattr(self, "_admin_btn"):
            self._admin_btn.config(bg=t["card_bg"], fg=t["running"],
                                    highlightbackground=t["border"])
        self._div1.config(bg=t["border"])
        self._div2.config(bg=t["border"])
        self._toolbar.config(bg=t["bg"])
        cur_search = self._search_var.get()
        self._search_entry.config(
            bg=t["card_bg"],
            fg=t["subtext"] if (not cur_search or cur_search == self._search_placeholder) else t["text"],
            highlightbackground=t["border"], highlightcolor=t["accent"],
            insertbackground=t["accent"])
        self._stopall_btn.config(bg=t["accent2"])
        self._outer.config(bg=t["bg"])
        self._canvas.config(bg=t["bg"])
        self._container.config(bg=t["bg"])
        self._footer_frame.config(bg=t["bg"])
        self._footer_lbl.config(bg=t["bg"], fg=t["subtext"])
        self._opacity_slider.config(bg=t["bg"], fg=t["subtext"], troughcolor=t["card_bg"])

        if hasattr(self, "_no_ahk_lbl"):
            self._no_ahk_lbl.config(bg=t["bg"], fg=t["accent2"])

        for card in self._card_refs:
            card["frame"].config(bg=t["card_bg"], highlightbackground=t["border"])
            card["inner"].config(bg=t["card_bg"])
            card["left"].config(bg=t["card_bg"])
            card["right"].config(bg=t["card_bg"])
            card["name_lbl"].config(bg=t["card_bg"], fg=t["text"])
            card["file_lbl"].config(bg=t["card_bg"], fg=t["subtext"])
            card["stats_lbl"].config(bg=t["card_bg"], fg=t["subtext"])
            card["timer_lbl"].config(bg=t["card_bg"], fg=t["subtext"])
            fn     = card["info"]["filename"]
            is_fav = fn in self._favs
            card["star_lbl"].config(bg=t["card_bg"],
                                     fg=t["accent"] if is_fav else t["subtext"])
            sv     = card["status_var"]
            sl     = card["status_lbl"]
            sl.config(bg=t["card_bg"])
            status = sv.get()
            if status == "RUNNING":   sl.config(fg=t["running"])
            elif status == "ACTIVE":  sl.config(fg=t["accent"])
            elif status == "PAUSED":  sl.config(fg=t["accent2"])
            else:                     sl.config(fg=t["stopped"])
            card["toggle"].apply_theme(t)

    # ── Script lifecycle ──────────────────────────────────────────────────────
    def _toggle(self, on, info, sv, sl, tog):
        if on:
            self._start(info, sv, sl, tog)
        else:
            self._stop(info["filename"], sv, sl, tog)

    def _start(self, info, sv, sl, tog):
        if not self.ahk_path:
            sv.set("NO AHK"); sl.config(fg=self._t("accent2")); return
        import datetime
        fn  = info["filename"]
        tmp = os.path.join(self.tmp_dir, fn)

        kb     = self._keybinds
        script = info["script"]
        script = script.replace("F6::",  f"{kb['start']}::")
        script = script.replace("F10::", f"{kb['stop']}::")
        script = script.replace("F12::", f"{kb['exit']}::")

        with open(tmp, "w", encoding="utf-8") as f:
            f.write(script)
        try:
            proc = subprocess.Popen([self.ahk_path, tmp],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            self.procs[fn] = proc
            sv.set("RUNNING"); sl.config(fg=self._t("running"))
            tog.set_state(1)

            entry = self._stats.get(fn, {"runs": 0, "last": "never"})
            entry["runs"] += 1
            entry["last"] = datetime.datetime.now().strftime("%d/%m %H:%M")
            self._stats[fn] = entry
            save_stats(self._stats)

            start_time = datetime.datetime.now()
            for card in self._card_refs:
                if card["info"]["filename"] == fn:
                    card["stats_lbl"].config(
                        text=f"runs: {entry['runs']}  ·  last: {entry['last']}")
                    self._run_timer(fn, start_time, card["timer_var"])
                    break

            threading.Thread(target=self._watch,
                             args=(proc, fn, sv, sl, tog), daemon=True).start()
            threading.Thread(target=self._hotkey_monitor,
                             args=(fn, sv, sl, tog), daemon=True).start()
        except Exception:
            sv.set("ERROR"); sl.config(fg=self._t("accent2"))

    def _stop(self, fn, sv, sl, tog):
        proc = self.procs.pop(fn, None)
        if proc and proc.poll() is None:
            proc.terminate()
        sv.set("STOPPED"); sl.config(fg=self._t("stopped"))
        tog.set_state(0)
        for card in self._card_refs:
            if card["info"]["filename"] == fn:
                card["timer_var"].set("")
                break

    def _run_timer(self, fn, start_time, timer_var):
        import datetime
        if fn not in self.procs:
            timer_var.set("")
            return
        elapsed = datetime.datetime.now() - start_time
        total_s = int(elapsed.total_seconds())
        h, rem  = divmod(total_s, 3600)
        m, s    = divmod(rem, 60)
        timer_var.set(f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}")
        self.after(1000, lambda: self._run_timer(fn, start_time, timer_var))

    def _hotkey_monitor(self, fn, sv, sl, tog):
        import ctypes, time
        VK_MAP = {
            "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
            "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
            "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
            "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F,
        }
        kb       = self._keybinds
        vk_start = VK_MAP.get(kb.get("start", "F6").upper(),  0x75)
        vk_stop  = VK_MAP.get(kb.get("stop",  "F10").upper(), 0x79)
        vk_exit  = VK_MAP.get(kb.get("exit",  "F12").upper(), 0x7B)

        GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
        prev_start = prev_stop = prev_exit = False

        def _apply(status, fg_key, tog_pos):
            sv.set(status)
            sl.config(fg=self._t(fg_key))
            tog.set_state(tog_pos)

        while fn in self.procs:
            s  = bool(GetAsyncKeyState(vk_start) & 0x8000)
            st = bool(GetAsyncKeyState(vk_stop)  & 0x8000)
            ex = bool(GetAsyncKeyState(vk_exit)  & 0x8000)

            if s  and not prev_start: self.after(0, lambda: _apply("ACTIVE",  "accent",  2))
            elif st and not prev_stop: self.after(0, lambda: _apply("PAUSED",  "accent2", 1))
            elif ex and not prev_exit: self.after(0, lambda: _apply("STOPPED", "stopped", 0))

            prev_start = s; prev_stop = st; prev_exit = ex
            time.sleep(0.08)

    def _watch(self, proc, fn, sv, sl, tog):
        proc.wait()
        if fn in self.procs:
            self.procs.pop(fn, None)
            def _on_stop():
                sv.set("STOPPED")
                sl.config(fg=self._t("stopped"))
                tog.set_state(0)
            self.after(0, _on_stop)

    # ── Search / filter ───────────────────────────────────────────────────────
    def _search_focus_in(self, _=None):
        if self._search_var.get() == self._search_placeholder:
            self._search_entry.delete(0, "end")
            self._search_entry.config(fg=self._t("text"))

    def _search_focus_out(self, _=None):
        if not self._search_var.get():
            self._search_entry.insert(0, self._search_placeholder)
            self._search_entry.config(fg=self._t("subtext"))

    def _filter_cards(self):
        query = self._search_var.get().strip().lower()
        if query == self._search_placeholder.lower():
            query = ""
        for card in self._card_refs:
            name = card["info"]["display_name"].lower()
            fn   = card["info"]["filename"].lower()
            if query == "" or query in name or query in fn:
                card["frame"].pack(fill="x", pady=6, padx=8)
            else:
                card["frame"].pack_forget()

    # ── Stop All ──────────────────────────────────────────────────────────────
    def _stop_all(self):
        for card in self._card_refs:
            fn = card["info"]["filename"]
            if fn in self.procs:
                self._stop(fn, card["status_var"], card["status_lbl"], card["toggle"])

    # ── Opacity ───────────────────────────────────────────────────────────────
    def _set_opacity(self, val):
        self.attributes("-alpha", int(val) / 100)

    # ── Favourites ────────────────────────────────────────────────────────────
    def _toggle_fav(self, fn, star_lbl):
        if fn in self._favs:
            self._favs.remove(fn)
            star_lbl.config(text="☆", fg=self._t("subtext"))
        else:
            self._favs.append(fn)
            star_lbl.config(text="★", fg=self._t("accent"))
        save_favs(self._favs)
        for card in self._card_refs:
            card["frame"].pack_forget()
        sorted_cards = sorted(self._card_refs,
                               key=lambda c: (0 if c["info"]["filename"] in self._favs else 1))
        for card in sorted_cards:
            card["frame"].pack(fill="x", pady=6, padx=8)

    # ── Hotkey Help ───────────────────────────────────────────────────────────
    def _open_hotkey_help(self):
        kb  = self._keybinds
        win = tk.Toplevel(self)
        win.title("Hotkey Reference")
        win.resizable(False, False)
        win.configure(bg=self._t("bg"))
        win.grab_set()
        t = self._theme

        tk.Label(win, text="Hotkey Reference", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        rows = [
            (kb["start"], "Start / activate the script"),
            (kb["stop"],  "Pause / stop the script"),
            (kb["exit"],  "Exit the script entirely"),
        ]
        frame = tk.Frame(win, bg=t["bg"], padx=30, pady=20)
        frame.pack()
        for key, desc in rows:
            row = tk.Frame(frame, bg=t["bg"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=key, font=self.font_status, bg=t["card_bg"],
                     fg=t["accent"], width=6, pady=4, relief="flat",
                     highlightbackground=t["border"], highlightthickness=1).pack(side="left")
            tk.Label(row, text=f"  {desc}", font=self.font_file,
                     bg=t["bg"], fg=t["text"], anchor="w").pack(side="left")

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)
        close_btn = tk.Label(win, text="Close", font=self.font_badge,
                              bg=t["card_bg"], fg=t["accent2"],
                              padx=16, pady=8, cursor="hand2",
                              highlightbackground=t["border"], highlightthickness=1)
        close_btn.pack(pady=12)
        close_btn.bind("<Button-1>", lambda e: win.destroy())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    # ── Keybind editor ────────────────────────────────────────────────────────
    def _open_keybind_editor(self):
        win = tk.Toplevel(self)
        win.title("Custom Keybinds")
        win.resizable(False, False)
        win.configure(bg=self._t("bg"))
        win.grab_set()
        t = self._theme

        tk.Label(win, text="Custom Keybinds", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        frame = tk.Frame(win, bg=t["bg"], padx=30, pady=20)
        frame.pack()

        labels = [("Start key", "start"), ("Stop key", "stop"), ("Exit key", "exit")]
        vars_  = {}
        for i, (lbl, key) in enumerate(labels):
            tk.Label(frame, text=lbl, font=self.font_file, bg=t["bg"],
                     fg=t["text"], anchor="w", width=12).grid(
                row=i, column=0, pady=6, sticky="w")
            v = tk.StringVar(value=self._keybinds[key])
            vars_[key] = v
            tk.Entry(frame, textvariable=v, font=self.font_file,
                     bg=t["card_bg"], fg=t["text"],
                     insertbackground=t["accent"],
                     relief="flat", width=10,
                     highlightbackground=t["border"],
                     highlightthickness=1).grid(row=i, column=1, padx=(10, 0), pady=6)

        tk.Label(frame, text="e.g. F6, F10, F12, ^F1 (Ctrl+F1)",
                 font=self.font_file, bg=t["bg"], fg=t["subtext"]
                 ).grid(row=len(labels), column=0, columnspan=2, pady=(4, 0))

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)
        btn_row = tk.Frame(win, bg=t["bg"], pady=12)
        btn_row.pack()

        def save():
            for key, v in vars_.items():
                self._keybinds[key] = v.get().strip()
            save_keybinds(self._keybinds)
            win.destroy()

        for text, cmd, col in [("Save", save, t["accent"]),
                                ("Cancel", win.destroy, t["accent2"])]:
            b = tk.Label(btn_row, text=text, font=self.font_badge,
                         bg=t["card_bg"], fg=col, padx=16, pady=8,
                         cursor="hand2",
                         highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="left", padx=8)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    # ── Auto-update ───────────────────────────────────────────────────────────
    def _bg_check_update(self):
        check_for_update(
            lambda v: self.after(0, lambda: self._show_update(v))
        )

    def _show_update(self, latest_version):
        show_update_prompt(
            self, latest_version, self.procs, self.tmp_dir,
            self.font_name, self.font_file, self.font_status, self.font_badge,
            self._theme,
        )

    # ── Admin panel ───────────────────────────────────────────────────────────
    def _open_admin_panel(self):
        t   = self._theme
        win = tk.Toplevel(self)
        win.title("User Management")
        win.resizable(False, False)
        win.configure(bg=t["bg"])
        win.grab_set()

        tk.Label(win, text="User Management", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        status_var = tk.StringVar()
        tk.Label(win, textvariable=status_var, font=self.font_file,
                 bg=t["bg"], fg=t["running"]).pack(pady=(6, 0))

        list_frame = tk.Frame(win, bg=t["bg"], padx=20, pady=10)
        list_frame.pack(fill="both")

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            remote_users, _ = fetch_remote_users()
            if not remote_users:
                tk.Label(list_frame, text="No users found.",
                         font=self.font_file, bg=t["bg"], fg=t["accent2"]).pack()
                return
            tk.Label(list_frame, text="USERNAME",
                     font=self.font_file, bg=t["bg"], fg=t["subtext"],
                     anchor="w").pack(fill="x", pady=(0, 4))
            tk.Frame(list_frame, bg=t["border"], height=1).pack(fill="x", pady=(0, 6))
            for uname in list(remote_users.keys()):
                row = tk.Frame(list_frame, bg=t["card_bg"],
                                highlightbackground=t["border"], highlightthickness=1)
                row.pack(fill="x", pady=3, ipady=6)
                tk.Label(row, text=uname, font=self.font_file, bg=t["card_bg"],
                          fg=t["text"], anchor="w", padx=8).pack(side="left")
            tk.Label(list_frame, text=f"{len(remote_users)} account(s) on file",
                     font=self.font_file, bg=t["bg"], fg=t["subtext"]).pack(pady=(8, 0))

        refresh()

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20, pady=(6, 0))
        btn_row = tk.Frame(win, bg=t["bg"], pady=10)
        btn_row.pack()
        for text, cmd, col in [("Refresh", refresh, t["accent"]),
                                ("Close",   win.destroy, t["accent2"])]:
            b = tk.Label(btn_row, text=text, font=self.font_badge,
                          bg=t["card_bg"], fg=col, padx=14, pady=7,
                          cursor="hand2",
                          highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="left", padx=6)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    # ── Change server ─────────────────────────────────────────────────────────
    def _change_server(self):
        self._stop_all()
        for proc in self.procs.values():
            try:
                proc.terminate()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self._change_server_requested = True
        self.destroy()

    # ── Blank window ──────────────────────────────────────────────────────────
    def _open_blank_window(self):
        t = self._theme
        self.withdraw()
        win = tk.Toplevel(self)
        win.title("Nebula")
        win.resizable(True, True)
        win.configure(bg=t["bg"])
        win.geometry("500x400")
        try:
            win.iconbitmap(resource_path("nebula.ico"))
        except Exception:
            pass

        def go_back():
            win.destroy()
            self.deiconify()

        win.protocol("WM_DELETE_WINDOW", go_back)

        header = tk.Frame(win, bg=t["bg"], padx=20, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="⬡ Nebula",
                 font=tkfont.Font(family="Segoe Script", size=13, weight="bold"),
                 bg=t["bg"], fg=t["accent"]).pack(side="left")

        back_btn = tk.Label(header, text="← Back", font=self.font_badge,
                             bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
                             cursor="hand2", relief="flat",
                             highlightbackground=t["border"], highlightthickness=1)
        back_btn.pack(side="right")
        back_btn.bind("<Button-1>", lambda e: go_back())

        for text, cmd in [("⚙ Theme", self._open_theme_editor),
                          ("⌨ Keybinds", self._open_keybind_editor),
                          ("? Help", self._open_hotkey_help)]:
            b = tk.Label(header, text=text, font=self.font_badge,
                          bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
                          cursor="hand2", relief="flat",
                          highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="right", padx=(0, 6))
            b.bind("<Button-1>", lambda e, c=cmd: c())

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        centre = tk.Frame(win, bg=t["bg"])
        centre.pack(fill="both", expand=True)
        tk.Label(centre, text="⬡",
                 font=tkfont.Font(family="Segoe Script", size=72, weight="bold"),
                 bg=t["bg"], fg=t["accent"]).pack(expand=True)

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth()  - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"+{x}+{y}")

    # ── Logout / Close ────────────────────────────────────────────────────────
    def _logout(self):
        clear_session()
        for proc in self.procs.values():
            try:
                proc.terminate()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self._logged_out = True
        self.destroy()

    def _on_close(self):
        for proc in self.procs.values():
            try:
                proc.terminate()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.destroy()
