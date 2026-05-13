from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
import json

import cv2
try:
    import ttkbootstrap as tb
except Exception:
    tb = None

from PIL import Image, ImageTk

from alertes import show_toast
from camera import CameraStream
from config import APP_TITLE, DATASET_DIR, THEME, CASCADE_PATH, CONSENT_PATH
from historique import get_recent_logs, get_stats, clear_logs, export_logs_csv, get_logs
from reconnaissance import (
    delete_user_everywhere,
    ensure_storage,
    get_user_by_id,
    load_users,
    next_user_id,
    save_users,
    train_model,
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_storage()
        self.title(APP_TITLE)
        self.geometry("1440x900")
        self.minsize(1280, 820)
        self.configure(bg=THEME.bg)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.camera = None
        self.camera_running = False
        self.current_frame = None
        self.log_filter = tk.StringVar(value="ALL")
        self.confidence_var = tk.DoubleVar(value=55.0)
        self.autorefresh_var = tk.BooleanVar(value=True)
        self.smooth_mode_var = tk.BooleanVar(value=True)
        self.nav_items = [
            ("dashboard", "Dashboard", "▣"),
            ("admin", "Admin", "◈"),
            ("settings", "Settings", "⚙"),
        ]
        self._build_styles()
        if self._ensure_rgpd_consent():
            self._build_layout()
            self._tick_clock()
            self.refresh_dashboard()
        else:
            self.after(0, self.destroy)

    def _build_styles(self):
        if tb is not None:
            self.style = tb.Style(theme="darkly")
        else:
            self.style = ttk.Style()
            self.style.theme_use("clam")
        self.option_add("*Font", ("Segoe UI", 10))
        self.style.configure("Sidebar.TFrame", background=THEME.panel)
        self.style.configure("Main.TFrame", background=THEME.bg)
        self.style.configure("Card.TFrame", background=THEME.panel, relief="flat")
        self.style.configure("CardTitle.TLabel", background=THEME.panel, foreground=THEME.muted, font=("Segoe UI", 10, "bold"))
        self.style.configure("CardValue.TLabel", background=THEME.panel, foreground=THEME.text, font=("Segoe UI", 24, "bold"))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Header.TLabel", background=THEME.bg, foreground=THEME.text, font=("Segoe UI", 22, "bold"))
        self.style.configure("SubHeader.TLabel", background=THEME.bg, foreground=THEME.muted, font=("Segoe UI", 10))
        self.style.configure("Toast.TFrame", background=THEME.panel)
        self.style.configure("ToastTitle.TLabel", background=THEME.panel, foreground=THEME.text, font=("Segoe UI", 11, "bold"))
        self.style.configure("ToastText.TLabel", background=THEME.panel, foreground=THEME.muted)
        self.style.configure("Treeview", background=THEME.panel, fieldbackground=THEME.panel, foreground=THEME.text, rowheight=30, borderwidth=0)
        self.style.configure("Treeview.Heading", background=THEME.panel_alt, foreground=THEME.text, font=("Segoe UI", 10, "bold"))
        self.style.configure("TScale", troughcolor=THEME.panel_alt, background=THEME.bg)

    def _ensure_rgpd_consent(self):
        if CONSENT_PATH.exists():
            try:
                CONSENT_PATH.write_text(json.dumps({"accepted": False, "version": "1.2"}, indent=2), encoding="utf-8")
            except Exception:
                pass

        dialog = tk.Toplevel(self)
        dialog.title("RGPD Consent v1.2")
        dialog.geometry("560x620")
        dialog.configure(bg=THEME.bg)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_rgpd_choice(dialog, False))
        dialog.update_idletasks()
        x = self.winfo_screenwidth() // 2 - 280
        y = self.winfo_screenheight() // 2 - 310
        dialog.geometry(f"+{x}+{y}")

        frame = tk.Frame(dialog, bg=THEME.panel, highlightthickness=1, highlightbackground="#17314b")
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        header = tk.Frame(frame, bg=THEME.panel)
        header.pack(fill="x", padx=18, pady=(18, 8))
        tk.Label(header, text="RGPD Consent Required", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Version 1.2", bg=THEME.panel, fg=THEME.accent_2, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 0))

        glass = tk.Frame(frame, bg="#0b1726", highlightthickness=1, highlightbackground="#1a3550")
        glass.pack(fill="both", expand=True, padx=18, pady=10)
        tk.Label(
            glass,
            text="This biometric application stores access logs and face data locally on this machine only. Please review the RGPD summary below and choose Accept or Deny.",
            bg="#0b1726",
            fg=THEME.muted,
            wraplength=460,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(16, 10))

        scroll_holder = tk.Frame(glass, bg="#0b1726")
        scroll_holder.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        canvas = tk.Canvas(scroll_holder, bg="#0b1726", highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(scroll_holder, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg="#0b1726")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _resize_canvas(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", _resize_canvas)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        policy_text = [
            ("Local storage only", "Biometric data and logs stay on this device."),
            ("Right to deletion", "You can delete a user and all related face images at any time."),
            ("SQLite audit logs", "Access events are recorded locally in a secure database."),
            ("Consent version 1.2", "This consent applies to the current application build."),
            ("Revocation", "You may refuse now or revoke later by deleting the consent file."),
            ("Usage scope", "The system is intended for academic and demo biometric access control use."),
        ]
        for title, desc in policy_text:
            row = tk.Frame(content, bg="#0f1d30", highlightthickness=1, highlightbackground="#17314b")
            row.pack(fill="x", pady=6, padx=2)
            tk.Label(row, text="?", bg="#0f1d30", fg=THEME.accent_2, font=("Segoe UI", 11, "bold"), width=2).pack(side="left", padx=(8, 0), pady=10)
            text_box = tk.Frame(row, bg="#0f1d30")
            text_box.pack(side="left", fill="both", expand=True, padx=4, pady=10)
            tk.Label(text_box, text=title, bg="#0f1d30", fg=THEME.text, font=("Segoe UI", 10, "bold"), anchor="w", justify="left").pack(anchor="w")
            tk.Label(text_box, text=desc, bg="#0f1d30", fg=THEME.muted, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=400).pack(anchor="w", pady=(3, 0))

        actions = tk.Frame(frame, bg=THEME.panel, highlightthickness=1, highlightbackground="#17314b")
        actions.pack(fill="x", padx=18, pady=(0, 18))
        tk.Label(actions, text="You must choose one option to continue.", bg=THEME.panel, fg=THEME.muted, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 6))
        btn_col = tk.Frame(actions, bg=THEME.panel)
        btn_col.pack(fill="x", padx=16, pady=(0, 12))
        tk.Button(
            btn_col,
            text="Accept",
            command=lambda: self._set_rgpd_choice(dialog, True),
            bg=THEME.success,
            fg="white",
            relief="flat",
            padx=18,
            pady=12,
        ).pack(fill="x", pady=(0, 10))
        tk.Button(
            btn_col,
            text="Deny",
            command=lambda: self._set_rgpd_choice(dialog, False),
            bg=THEME.danger,
            fg="white",
            relief="flat",
            padx=18,
            pady=12,
        ).pack(fill="x")

        self.wait_window(dialog)
        return getattr(self, "_rgpd_accepted", False)

    def _set_rgpd_choice(self, dialog, accepted: bool):
        self._rgpd_accepted = accepted
        CONSENT_PATH.write_text(json.dumps({"accepted": accepted, "version": "1.2"}, indent=2), encoding="utf-8")
        dialog.grab_release()
        dialog.destroy()

    def _build_layout(self):
        root = tk.Frame(self, bg=THEME.bg)
        root.pack(fill="both", expand=True)
        topbar = tk.Frame(root, bg="#0b1726", height=52, highlightthickness=1, highlightbackground="#17314b")
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)
        tk.Label(topbar, text="SBACS", bg="#0b1726", fg=THEME.accent_2, font=("Segoe UI", 12, "bold")).pack(side="left", padx=18)
        tk.Label(topbar, text="Smart Biometric Access Control System", bg="#0b1726", fg=THEME.text, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        tk.Button(topbar, text="Dashboard", command=lambda: self.show_page("dashboard"), bg=THEME.panel_alt, fg=THEME.text, relief="flat", padx=12, pady=6).pack(side="right", padx=(8, 18))
        tk.Button(topbar, text="Admin", command=lambda: self.show_page("admin"), bg=THEME.panel_alt, fg=THEME.text, relief="flat", padx=12, pady=6).pack(side="right")
        tk.Button(topbar, text="Settings", command=lambda: self.show_page("settings"), bg=THEME.panel_alt, fg=THEME.text, relief="flat", padx=12, pady=6).pack(side="right", padx=(0, 8))

        body = tk.Frame(root, bg=THEME.bg)
        body.pack(side="top", fill="both", expand=True)
        sidebar = tk.Frame(body, bg=THEME.panel, width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        main = tk.Frame(body, bg=THEME.bg)
        main.pack(side="right", fill="both", expand=True)
        header = tk.Frame(main, bg=THEME.bg, height=90)
        header.pack(fill="x", padx=24, pady=(20, 10))
        header.pack_propagate(False)
        tk.Label(header, text="Smart Biometric Access Control System", bg=THEME.bg, fg=THEME.text, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(header, text="Cybersecurity-grade biometric monitoring, logging, and administration", bg=THEME.bg, fg=THEME.muted, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        self.content = tk.Frame(main, bg=THEME.bg)
        self.content.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.pages = {}
        self._build_sidebar(sidebar)
        self._build_dashboard()
        self._build_admin()
        self._build_settings()
        self.show_page("dashboard")

    def _sidebar_button(self, parent, text, command, icon=""):
        row = tk.Frame(parent, bg=THEME.panel_alt, highlightthickness=1, highlightbackground="#16314a")
        row.pack_propagate(False)
        btn = tk.Button(
            row,
            command=command,
            bg=THEME.panel_alt,
            fg=THEME.text,
            activebackground=THEME.accent,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            text=f"{icon}   {text}".strip(),
        )
        btn.pack(fill="both", expand=True)
        return row

    def _build_sidebar(self, parent):
        brand = tk.Frame(parent, bg=THEME.panel, padx=18, pady=18)
        brand.pack(fill="x", padx=16, pady=(18, 12))
        tk.Label(brand, text="SBACS", bg=THEME.panel, fg=THEME.accent_2, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(brand, text="Smart Biometric Access Control System", bg=THEME.panel, fg=THEME.text, wraplength=220, justify="left", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        tk.Label(brand, text="Enterprise biometric operations console", bg=THEME.panel, fg=THEME.muted, wraplength=220, justify="left").pack(anchor="w")
        status = tk.Frame(parent, bg=THEME.panel_alt, highlightthickness=1, highlightbackground="#1b3a57")
        status.pack(fill="x", padx=16, pady=(0, 14))
        tk.Label(status, text="SYSTEM STATUS", bg=THEME.panel_alt, fg=THEME.muted, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(status, text="ONLINE", bg=THEME.panel_alt, fg=THEME.accent_2, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(0, 10))
        logs_box = tk.Frame(parent, bg=THEME.panel, highlightthickness=1, highlightbackground="#18344d")
        logs_box.pack(fill="both", expand=False, padx=16, pady=(0, 14))
        top_logs = tk.Frame(logs_box, bg=THEME.panel)
        top_logs.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(top_logs, text="Recent Logs", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Combobox(top_logs, textvariable=self.log_filter, values=["ALL", "AUTHORIZED", "REFUSED"], width=12, state="readonly").pack(side="right")
        columns = ("User", "Date", "Time", "Status", "Confidence")
        self.left_logs_table = ttk.Treeview(logs_box, columns=columns, show="headings", height=10)
        for c in columns:
            self.left_logs_table.heading(c, text=c)
            self.left_logs_table.column(c, width=90, anchor="center")
        self.left_logs_table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.left_logs_table.tag_configure("AUTHORIZED", background="#0f2a24")
        self.left_logs_table.tag_configure("REFUSED", background="#2a1218")
        for key, label, icon in self.nav_items:
            self._sidebar_button(parent, label, lambda k=key: self.show_page(k), icon=icon).pack(fill="x", padx=16, pady=6)
        tk.Frame(parent, bg=THEME.panel).pack(fill="x", padx=16, pady=10)
        self._sidebar_button(parent, "Refresh", self.refresh_dashboard, icon="↻").pack(fill="x", padx=16, pady=6)
        self._sidebar_button(parent, "Retrain Model", self.retrain_model, icon="⟲").pack(fill="x", padx=16, pady=6)
        self._sidebar_button(parent, "Add User", self.add_user, icon="+").pack(fill="x", padx=16, pady=6)
        self._sidebar_button(parent, "Clear Logs", self.clear_logs_action, icon="✕").pack(fill="x", padx=16, pady=6)

    def _card(self, parent, title, value):
        frame = tk.Frame(parent, bg=THEME.panel, bd=0, highlightthickness=1, highlightbackground="#18344d")
        tk.Label(frame, text=title, bg=THEME.panel, fg=THEME.muted, font=("Segoe UI", 9, "bold"), justify="left").pack(anchor="w", padx=18, pady=(16, 2))
        label = tk.Label(frame, text=value, bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 26, "bold"))
        label.pack(anchor="w", padx=18, pady=(0, 16))
        return frame, label

    def _build_dashboard(self):
        page = tk.Frame(self.content, bg=THEME.bg)
        self.pages["dashboard"] = page
        self.dashboard_cards = {}
        hero = tk.Frame(page, bg=THEME.panel, highlightthickness=1, highlightbackground="#17314b")
        hero.pack(fill="x", pady=(0, 14))
        left = tk.Frame(hero, bg=THEME.panel)
        left.pack(side="left", fill="both", expand=True, padx=18, pady=18)
        tk.Label(left, text="Live Security Operations", bg=THEME.panel, fg=THEME.accent_2, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(left, text="Modern biometric access control with real-time recognition and secure audit logging.", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 18, "bold"), wraplength=700, justify="left").pack(anchor="w", pady=(8, 6))
        tk.Label(left, text="Smooth camera stream, RGPD deletion, exportable logs, and enterprise-grade dashboard analytics.", bg=THEME.panel, fg=THEME.muted, wraplength=760, justify="left").pack(anchor="w")
        right_hero = tk.Frame(hero, bg=THEME.panel)
        right_hero.pack(side="right", padx=18, pady=18)
        self.hero_clock = tk.Label(right_hero, text="--:--:--", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 24, "bold"))
        self.hero_clock.pack(anchor="e")
        tk.Label(right_hero, text="Security Center", bg=THEME.panel, fg=THEME.accent_2, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(4, 0))
        cards = tk.Frame(page, bg=THEME.bg)
        cards.pack(fill="x")
        titles = [("Total Users", "0"), ("Authorized Today", "0"), ("Refused Today", "0"), ("Success Rate", "0%")]
        for i, (title, val) in enumerate(titles):
            f, lab = self._card(cards, title, val)
            f.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            cards.grid_columnconfigure(i, weight=1)
            self.dashboard_cards[title] = lab
        body = tk.Frame(page, bg=THEME.bg)
        body.pack(fill="both", expand=True, pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        center_wrap = tk.Frame(body, bg=THEME.bg)
        center_wrap.grid(row=0, column=0, sticky="nsew")
        center_wrap.grid_rowconfigure(0, weight=1)
        center_wrap.grid_columnconfigure(0, weight=1)

        self.camera_panel = tk.Frame(center_wrap, bg=THEME.panel, width=860, height=620, highlightthickness=1, highlightbackground="#18344d")
        self.camera_panel.place(relx=0.5, rely=0.5, anchor="center")
        self.camera_panel.pack_propagate(False)
        cam_top = tk.Frame(self.camera_panel, bg=THEME.panel)
        cam_top.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(cam_top, text="Live Camera", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 13, "bold")).pack(side="left")
        self.camera_badge = tk.Label(cam_top, text="Smooth feed", bg=THEME.panel_alt, fg=THEME.accent_2, font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.camera_badge.pack(side="right")
        camera_stage = tk.Frame(self.camera_panel, bg="#050b14", highlightthickness=1, highlightbackground="#17314b")
        camera_stage.pack(fill="both", expand=True, padx=12, pady=12)
        self.camera_label = tk.Label(camera_stage, bg="#050b14")
        self.camera_label.pack(fill="both", expand=True, padx=10, pady=10)

        right = tk.Frame(body, bg=THEME.bg, width=10)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        actions = tk.Frame(right, bg=THEME.bg)
        actions.grid(row=0, column=0, sticky="ew")
        tk.Label(actions, text="Quick Actions", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        for text, cmd in [("Refresh", self.refresh_dashboard), ("Pause Camera", self.toggle_camera_pause), ("Retrain Model", self.retrain_model), ("Add User", self.add_user), ("Open Admin", lambda: self.show_page("admin"))]:
            tk.Button(actions, text=text, command=cmd, bg=THEME.accent, fg="white", relief="flat", padx=14, pady=10).pack(fill="x", padx=16, pady=6)
        self.camera_status = tk.Label(actions, text="Camera: inactive", bg=THEME.panel, fg=THEME.muted, font=("Segoe UI", 10, "bold"))
        self.camera_status.pack(anchor="w", padx=16, pady=(10, 0))
        self.cam_tip = tk.Label(actions, text="Tip: Use the settings page to tune recognition sensitivity.", bg=THEME.panel, fg=THEME.muted, wraplength=360, justify="left")
        self.cam_tip.pack(anchor="w", padx=16, pady=(10, 0))
        self.log_filter.trace_add("write", lambda *_: self.refresh_dashboard())
        self.logs_table = self.left_logs_table

    def _build_admin(self):
        page = tk.Frame(self.content, bg=THEME.bg)
        self.pages["admin"] = page
        top = tk.Frame(page, bg=THEME.panel, highlightthickness=1, highlightbackground="#17314b")
        top.pack(fill="x")
        header = tk.Frame(top, bg=THEME.panel)
        header.pack(fill="x", padx=18, pady=(16, 2))
        tk.Label(header, text="Admin Panel", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 18, "bold")).pack(side="left", anchor="w")
        tk.Button(header, text="Back to Dashboard", command=lambda: self.show_page("dashboard"), bg=THEME.accent, fg="white", relief="flat", padx=14, pady=8).pack(side="right")
        tk.Label(top, text="User lifecycle, dataset capture, model training, and compliance deletion", bg=THEME.panel, fg=THEME.muted).pack(anchor="w", padx=18, pady=(0, 16))
        controls = tk.Frame(page, bg=THEME.bg)
        controls.pack(fill="x", pady=(0, 12))
        for text, cmd in [("Add User", self.add_user), ("Capture Dataset", self.capture_dataset), ("Train Model", self.retrain_model), ("Search User", self.search_user), ("Delete User", self.delete_user_ui), ("Export Logs", self.export_logs_ui)]:
            tk.Button(controls, text=text, command=cmd, bg=THEME.panel_alt, fg=THEME.text, relief="flat", padx=14, pady=10).pack(side="left", padx=8)
        info = tk.Frame(page, bg=THEME.bg)
        info.pack(fill="x", pady=(0, 10))
        self.admin_summary = tk.Label(info, text="Dataset status ready", bg=THEME.bg, fg=THEME.muted, font=("Segoe UI", 10, "italic"))
        self.admin_summary.pack(anchor="w")
        self.users_table = ttk.Treeview(page, columns=("ID", "Name", "Role", "Dataset"), show="headings", height=18)
        for c in ("ID", "Name", "Role", "Dataset"):
            self.users_table.heading(c, text=c)
            self.users_table.column(c, width=180, anchor="w")
        self.users_table.pack(fill="both", expand=True)

    def _build_settings(self):
        page = tk.Frame(self.content, bg=THEME.bg)
        self.pages["settings"] = page
        header = tk.Frame(page, bg=THEME.panel, highlightthickness=1, highlightbackground="#17314b")
        header.pack(fill="x")
        tk.Label(header, text="Settings", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(header, text="Tune recognition sensitivity and live-stream behavior", bg=THEME.panel, fg=THEME.muted).pack(anchor="w", padx=18, pady=(0, 16))
        box = tk.Frame(page, bg=THEME.panel, highlightthickness=1, highlightbackground="#18344d")
        box.pack(fill="x")
        tk.Label(box, text="Recognition threshold", bg=THEME.panel, fg=THEME.text, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Scale(box, from_=35, to=85, orient="horizontal", resolution=1, variable=self.confidence_var, bg=THEME.panel, fg=THEME.text, highlightthickness=0, troughcolor=THEME.panel_alt, command=self._apply_threshold).pack(fill="x", padx=16)
        self.threshold_label = tk.Label(box, text="Current threshold: 55", bg=THEME.panel, fg=THEME.muted)
        self.threshold_label.pack(anchor="w", padx=16, pady=(0, 16))
        opts = tk.Frame(page, bg=THEME.bg)
        opts.pack(fill="x", pady=(12, 0))
        tk.Checkbutton(opts, text="Auto refresh dashboard", variable=self.autorefresh_var, bg=THEME.bg, fg=THEME.text, selectcolor=THEME.panel, activebackground=THEME.bg).pack(anchor="w")
        tk.Checkbutton(opts, text="Smooth mode (lighter detection load)", variable=self.smooth_mode_var, bg=THEME.bg, fg=THEME.text, selectcolor=THEME.panel, activebackground=THEME.bg, command=self._sync_smooth_mode).pack(anchor="w", pady=(6, 0))
        actions = tk.Frame(page, bg=THEME.bg)
        actions.pack(fill="x", pady=(18, 0))
        tk.Button(actions, text="Export Logs CSV", command=self.export_logs_ui, bg=THEME.panel_alt, fg=THEME.text, relief="flat", padx=14, pady=10).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Open Dashboard", command=lambda: self.show_page("dashboard"), bg=THEME.accent, fg="white", relief="flat", padx=14, pady=10).pack(side="left")

    def show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        if name == "dashboard":
            self.start_camera()
        else:
            self.stop_camera()
        self.refresh_dashboard()

    def refresh_dashboard(self):
        stats = get_stats()
        self.dashboard_cards["Total Users"].config(text=str(stats["total_users"]))
        self.dashboard_cards["Authorized Today"].config(text=str(stats["authorized_today"]))
        self.dashboard_cards["Refused Today"].config(text=str(stats["refused_today"]))
        self.dashboard_cards["Success Rate"].config(text=f"{stats['success_rate']}%")
        for tree in (self.logs_table, self.users_table):
            for row in tree.get_children():
                tree.delete(row)
        for row in get_logs(status=None, limit=30):
            if self.log_filter.get() == "ALL" or self.log_filter.get() == row[3]:
                tag = row[3]
                self.logs_table.insert("", "end", values=row, tags=(tag,))
        for user in load_users():
            user_id = str(user.get("id"))
            dataset_dir = DATASET_DIR / f"user_{user_id}"
            dataset_count = len(list(dataset_dir.glob("*.png"))) if dataset_dir.exists() else 0
            self.users_table.insert("", "end", values=(user_id, user.get("name", ""), user.get("role", "Employee"), dataset_count))
        if hasattr(self, "admin_summary"):
            self.admin_summary.config(text=f"Registered users: {stats['total_users']} | Logs visible: {len(self.logs_table.get_children())}")
        if self.camera:
            paused = "paused" if self.camera.paused else "active"
            self.camera_status.config(text=f"Camera: {paused}")
            if self.smooth_mode_var.get():
                self.camera_badge.config(text="Smooth mode enabled")
            else:
                self.camera_badge.config(text="High detail mode")

    def start_camera(self):
        if self.camera and self.camera.running:
            return
        try:
            self.camera = CameraStream(on_frame=self.render_frame, on_event=self.on_recognition_event)
            self.camera.process_scale = 0.58 if self.smooth_mode_var.get() else 0.8
            self.camera.recognizer.confidence_threshold = self.confidence_var.get()
            self.camera.start()
        except Exception as exc:
            show_toast(self, "Camera error", str(exc), kind="error")

    def stop_camera(self):
        if self.camera:
            self.camera.stop()

    def render_frame(self, frame):
        self.current_frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img = img.resize((900, 600), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        self.camera_label.after(0, lambda: self._set_camera_image(tk_img))

    def _set_camera_image(self, tk_img):
        self.camera_label.configure(image=tk_img)
        self.camera_label.image = tk_img
        if self.camera:
            state = "paused" if self.camera.paused else "active"
            self.camera_status.config(text=f"Camera: {state}")

    def on_recognition_event(self, det):
        show_toast(self, "Access granted", f"{det['label']} recognized with confidence {det['confidence']}", kind="success")
        if self.autorefresh_var.get():
            self.after(0, self.refresh_dashboard)

    def add_user(self):
        name = simpledialog.askstring("Add user", "Full name:", parent=self)
        if not name:
            return
        role = simpledialog.askstring("Add user", "Role:", parent=self) or "Employee"
        users = load_users()
        user_id = next_user_id(users)
        users.append({"id": user_id, "name": name.strip(), "role": role.strip()})
        save_users(users)
        (DATASET_DIR / f"user_{user_id}").mkdir(exist_ok=True)
        show_toast(self, "User created", f"{name} registered with ID {user_id}", kind="success")
        self.refresh_dashboard()

    def capture_dataset(self):
        user_id = simpledialog.askstring("Capture dataset", "User ID:", parent=self)
        user = get_user_by_id(user_id) if user_id else None
        if not user:
            messagebox.showerror("Error", "User not found")
            return
        directory = DATASET_DIR / f"user_{user_id}"
        directory.mkdir(exist_ok=True)
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Camera unavailable")
            return
        cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
        if cascade.empty():
            messagebox.showwarning("Warning", "Haar cascade file not found. Dataset capture will use raw frames.")
        count = 0
        while count < 50:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.3, 5) if not cascade.empty() else [(50, 50, frame.shape[1] - 100, frame.shape[0] - 100)]
            for (x, y, w, h) in faces[:1]:
                face = gray[y : y + h, x : x + w]
                if face.size == 0:
                    continue
                face = cv2.resize(face, (200, 200))
                cv2.imwrite(str(directory / f"{count + 1}.png"), face)
                count += 1
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 140), 2)
                cv2.putText(frame, f"Captured {count}/50", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 140), 2)
            cv2.imshow("Capture dataset", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        cap.release()
        cv2.destroyAllWindows()
        show_toast(self, "Dataset ready", f"Captured {count} images for {user['name']}", kind="success")
        self.refresh_dashboard()

    def retrain_model(self):
        def worker():
            try:
                train_model()
                self.after(0, lambda: show_toast(self, "Model trained", "LBPH model updated successfully", kind="success"))
            except Exception as exc:
                self.after(0, lambda: show_toast(self, "Training failed", str(exc), kind="error"))
        threading.Thread(target=worker, daemon=True).start()

    def search_user(self):
        query = simpledialog.askstring("Search user", "Search by name or ID:", parent=self)
        if not query:
            return
        query = query.lower().strip()
        matches = [u for u in load_users() if query in str(u.get("id", "")).lower() or query in str(u.get("name", "")).lower()]
        if not matches:
            messagebox.showinfo("Search", "No users found")
            return
        text = "\n".join(f"{u.get('id')} - {u.get('name')} ({u.get('role','Employee')})" for u in matches)
        messagebox.showinfo("Search results", text)

    def delete_user_ui(self):
        user_id = simpledialog.askstring("Delete user", "User ID to delete:", parent=self)
        if not user_id:
            return
        user = get_user_by_id(user_id)
        if not user:
            messagebox.showerror("Error", "User not found")
            return
        if not messagebox.askyesno("Confirm deletion", f"Delete {user.get('name')} and all dataset files?"):
            return
        delete_user_everywhere(user_id)
        show_toast(self, "User deleted", f"User {user.get('name')} removed completely", kind="warning")
        self.refresh_dashboard()

    def clear_logs_action(self):
        if messagebox.askyesno("Clear logs", "Delete all security logs?"):
            clear_logs()
            self.refresh_dashboard()
            show_toast(self, "Logs cleared", "All log entries removed", kind="warning")

    def export_logs_ui(self):
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            title="Export logs as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="security_logs.csv",
        )
        if not path:
            return
        export_logs_csv(path)
        show_toast(self, "Export complete", f"Logs exported to {path}", kind="success")

    def toggle_camera_pause(self):
        if not self.camera:
            return
        paused = self.camera.toggle_pause()
        show_toast(self, "Camera paused" if paused else "Camera resumed", "Live feed state updated", kind="info")

    def _apply_threshold(self, *_):
        value = float(self.confidence_var.get())
        self.threshold_label.config(text=f"Current threshold: {int(value)}")
        if self.camera:
            self.camera.recognizer.confidence_threshold = value
        show_toast(self, "Threshold updated", f"Recognition threshold set to {int(value)}", kind="info", timeout=1800)

    def _sync_smooth_mode(self):
        if self.camera:
            self.camera.process_scale = 0.58 if self.smooth_mode_var.get() else 0.8
        self.refresh_dashboard()

    def _tick_clock(self):
        if hasattr(self, "hero_clock"):
            from datetime import datetime

            self.hero_clock.config(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    def inspect_log_row(self, event):
        item = self.logs_table.identify_row(event.y)
        if not item:
            return
        values = self.logs_table.item(item, "values")
        messagebox.showinfo(
            "Log details",
            f"User: {values[0]}\nDate: {values[1]}\nTime: {values[2]}\nStatus: {values[3]}\nConfidence: {values[4]}",
        )

    def on_close(self):
        self.stop_camera()
        self.destroy()
