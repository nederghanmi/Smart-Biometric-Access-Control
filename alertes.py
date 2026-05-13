from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Toast(ttk.Frame):
    def __init__(self, master, title: str, message: str, kind: str = "info", timeout: int = 2500):
        super().__init__(master, padding=12)
        colors = {
            "info": "#2f80ff",
            "success": "#1dd1a1",
            "warning": "#ffb400",
            "error": "#ff5c77",
        }
        self.configure(style="Toast.TFrame")
        ttk.Label(self, text=title, style="ToastTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text=message, style="ToastText.TLabel", wraplength=340).pack(anchor="w", pady=(4, 0))
        self._bar = tk.Frame(self, height=3, bg=colors.get(kind, "#2f80ff"))
        self._bar.pack(fill="x", pady=(10, 0))
        self.pack(side="top", anchor="ne", padx=18, pady=18)
        self.after(timeout, self.destroy)


def show_toast(master, title: str, message: str, kind: str = "info", timeout: int = 2500):
    return Toast(master, title, message, kind=kind, timeout=timeout)

