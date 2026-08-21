#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Three-step Douyin Cookie helper.

The helper opens a temporary Playwright browser context.  It does not read
Chrome/Edge profile databases or passwords.  After the user scans the QR code
and Douyin creates a session, the Cookie is shown and copied to the clipboard.
Saving it to the local config file remains an explicit user action.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    print("无法加载 tkinter，请使用标准 Python 安装后重试。")
    raise SystemExit(1)

from cookie_utils import load_config, normalize_cookie, save_config, validate_cookie


PROJECT_DIR = Path(__file__).resolve().parent
DOUYIN_URL = "https://www.douyin.com/"


def find_browser_executable():
    """Return a locally installed Chrome/Edge executable, if available."""
    config = load_config()
    configured = [config.get("chrome_path", ""), config.get("edge_path", "")]
    candidates = [Path(path) for path in configured if path]

    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_name)
        if not root:
            continue
        root_path = Path(root)
        candidates.extend(
            (
                root_path / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                root_path / "Google" / "Chrome" / "Application" / "chrome.exe",
                root_path / "Chromium" / "Application" / "chrome.exe",
            )
        )

    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def cookie_string_from_browser_cookies(cookies):
    """Convert Playwright cookie dictionaries to a request Cookie header."""
    pairs = []
    for cookie in cookies:
        name = str(cookie.get("name", "")).strip()
        value = str(cookie.get("value", ""))
        if name and value:
            pairs.append(f"{name}={value}")
    return normalize_cookie("; ".join(pairs))


class CookieHelper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("音符 Cookie 自动获取")
        self.geometry("780x560")
        self.minsize(680, 500)

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.cookie_value = ""
        self.polling = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.after(300, self.start_login)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="音符 Cookie 自动获取",
            font=("Microsoft YaHei UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text="启动后会自动打开临时音符登录窗口，扫码成功后自动显示并复制 Cookie。",
            foreground="#555555",
        ).pack(anchor="w", pady=(4, 12))

        steps = (
            "三步完成：\n"
            "1. 双击获取音符Cookie.bat。\n"
            "2. 在弹出的音符页面扫码登录。\n"
            "3. 登录成功后，本窗口自动显示 Cookie 并复制到剪贴板。\n\n"
            "安全说明：使用临时浏览器会话，不读取现有 Chrome/Edge 的 Cookie 数据库或密码。"
        )
        step_box = tk.Text(outer, height=7, wrap="word", relief="solid", borderwidth=1)
        step_box.insert("1.0", steps)
        step_box.configure(state="disabled", background="#f7f7f7")
        step_box.pack(fill="x", pady=(0, 12))

        self.status_var = tk.StringVar(value="正在准备临时登录窗口……")
        ttk.Label(outer, textvariable=self.status_var, foreground="#555555").pack(
            anchor="w", pady=(0, 5)
        )

        ttk.Label(outer, text="获取到的 Cookie（仅显示在本机）：").pack(anchor="w")
        self.cookie_text = tk.Text(outer, height=10, wrap="word", undo=False)
        self.cookie_text.pack(fill="both", expand=True, pady=(4, 8))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(8, 0))
        self.copy_btn = ttk.Button(
            buttons, text="复制 Cookie", command=self.copy_cookie, state="disabled"
        )
        self.copy_btn.pack(side="left")
        self.save_btn = ttk.Button(
            buttons,
            text="保存到 config.ini",
            command=self.save_cookie,
            state="disabled",
        )
        self.save_btn.pack(side="left", padx=8)
        ttk.Button(buttons, text="重新打开登录页", command=self.start_login).pack(
            side="left"
        )
        ttk.Button(buttons, text="关闭", command=self.close_app).pack(side="right")

    def start_login(self):
        """Open Douyin automatically in a temporary browser context."""
        self.stop_browser()
        self.cookie_value = ""
        self.cookie_text.delete("1.0", "end")
        self.copy_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.status_var.set("正在打开音符登录页面……")

        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()
            executable_path = find_browser_executable()
            launch_kwargs = {"headless": False}
            if executable_path:
                launch_kwargs["executable_path"] = executable_path

            self.browser = self.playwright.chromium.launch(**launch_kwargs)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            try:
                self.page.goto(DOUYIN_URL, wait_until="domcontentloaded", timeout=20_000)
            except Exception:
                # The browser may still be usable when the page load times out.
                pass

            self.status_var.set("请在弹出的音符页面扫码登录，登录成功后会自动获取 Cookie。")
            self.polling = True
            self.after(1000, self.poll_login)
        except ImportError:
            self.status_var.set("缺少 Playwright 依赖。")
            messagebox.showerror(
                "缺少依赖",
                "请先运行：\n\npython -m pip install playwright\n\n"
                "然后重新打开本脚本。",
                parent=self,
            )
        except Exception as exc:
            self.stop_browser()
            self.status_var.set("登录窗口启动失败。")
            messagebox.showerror(
                "启动失败",
                f"无法启动浏览器：{exc}\n\n"
                "如果电脑没有 Chrome/Edge，请运行：\n"
                "python -m playwright install chromium",
                parent=self,
            )

    def poll_login(self):
        if not self.polling or not self.context:
            return

        try:
            cookies = self.context.cookies([DOUYIN_URL])
            cookie_value = cookie_string_from_browser_cookies(cookies)
            valid, _message = validate_cookie(cookie_value)
            if valid:
                self.show_cookie(cookie_value)
                return
            self.status_var.set("等待扫码登录……")
            self.after(1000, self.poll_login)
        except Exception:
            self.polling = False
            self.status_var.set("登录窗口已关闭，请点击“重新打开登录页”。")

    def show_cookie(self, cookie_value):
        self.polling = False
        self.cookie_value = cookie_value
        self.cookie_text.delete("1.0", "end")
        self.cookie_text.insert("1.0", cookie_value)
        self.copy_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.copy_cookie(show_message=False)
        self.status_var.set("登录成功：Cookie 已显示，并已复制到剪贴板。")
        self.stop_browser()
        messagebox.showinfo(
            "获取成功",
            "已检测到音符登录状态。Cookie 已显示在窗口中并复制到剪贴板。\n\n"
            "请勿把 Cookie 发送给他人或提交到 GitHub。",
            parent=self,
        )

    def copy_cookie(self, show_message=True):
        if not self.cookie_value:
            return
        self.clipboard_clear()
        self.clipboard_append(self.cookie_value)
        self.update()
        if show_message:
            messagebox.showinfo("复制成功", "Cookie 已复制到剪贴板。", parent=self)

    def save_cookie(self):
        if not self.cookie_value:
            return
        try:
            config = load_config()
            config["cookie"] = self.cookie_value
            save_config(config)
            messagebox.showinfo(
                "保存成功",
                f"Cookie 已保存到本地配置：\n{PROJECT_DIR / 'config.ini'}\n\n"
                "该文件已被 .gitignore 忽略，不会被 Git 提交。",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def stop_browser(self):
        self.polling = False
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    def close_app(self):
        self.stop_browser()
        self.destroy()


def main():
    os.chdir(PROJECT_DIR)
    app = CookieHelper()
    app.mainloop()


if __name__ == "__main__":
    main()
