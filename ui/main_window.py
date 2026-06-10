"""主窗口：左侧导航（桌面整理 / 软件卸载）+ 右侧内容区。"""
import tkinter.messagebox as mbox

import customtkinter as ctk

from core.version import APP_NAME, APP_VERSION

from .organize_page import OrganizePage
from .uninstall_page import UninstallPage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("900x600")
        self.minsize(760, 520)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()
        self.show_page("organize")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=170, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            sidebar, text="桌面清理\n小助手",
            font=ctk.CTkFont(size=20, weight="bold"), justify="left",
        ).grid(row=0, column=0, padx=20, pady=(24, 20), sticky="w")

        self.nav_organize = ctk.CTkButton(
            sidebar, text="🗂  桌面整理", anchor="w",
            command=lambda: self.show_page("organize"),
        )
        self.nav_organize.grid(row=1, column=0, padx=14, pady=6, sticky="ew")

        self.nav_uninstall = ctk.CTkButton(
            sidebar, text="🗑  软件卸载", anchor="w",
            command=lambda: self.show_page("uninstall"),
        )
        self.nav_uninstall.grid(row=2, column=0, padx=14, pady=6, sticky="ew")

        self.health_btn = ctk.CTkButton(
            sidebar, text="🔎 环境自检", anchor="w", fg_color="#3f6f4f",
            hover_color="#345e43", command=self.on_healthcheck,
        )
        self.health_btn.grid(row=3, column=0, padx=14, pady=6, sticky="ew")

        ctk.CTkLabel(
            sidebar, text=f"v{APP_VERSION}", text_color=("gray50", "gray60"),
        ).grid(row=6, column=0, padx=20, pady=12, sticky="sw")

    def _build_content(self):
        self.container = ctk.CTkFrame(self, fg_color=("gray95", "gray13"))
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.pages = {
            "organize": OrganizePage(self.container),
            "uninstall": UninstallPage(self.container),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, key: str):
        self.pages[key].tkraise()
        active = ("#1f6aa5", "#1f6aa5")
        inactive = "transparent"
        self.nav_organize.configure(fg_color=active if key == "organize" else inactive)
        self.nav_uninstall.configure(fg_color=active if key == "uninstall" else inactive)

    def on_healthcheck(self):
        results = run_healthcheck()
        lines = []
        all_ok = True
        for item in results:
            ok = item["ok"]
            all_ok = all_ok and ok
            icon = "✅" if ok else "⚠️"
            lines.append(f"{icon} {item['name']}：{item['detail']}")
        title = "环境自检通过" if all_ok else "环境自检完成（有提醒）"
        mbox.showinfo(title, "\n".join(lines))
