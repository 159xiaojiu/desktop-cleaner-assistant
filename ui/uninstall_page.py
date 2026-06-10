"""软件卸载页：分组筛选 + 多选 + 批量卸载（可选彻底清残留），全部在本工具内完成。"""
import threading
import tkinter.messagebox as mbox

import customtkinter as ctk

from core import uninstaller


class UninstallPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._apps = []
        self._check_vars = {}  # app.name -> BooleanVar
        self._busy = False
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="软件卸载", font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(18, 4))

        tip = ctk.CTkLabel(
            self,
            text="勾选要卸载的软件（可多选），点【卸载选中】即可，全部在本工具内完成，不需要再开别的软件。"
                 "默认只显示【可能想卸载】这一类；系统/常用软件已自动归类并隐藏，避免误删。",
            text_color=("gray40", "gray70"), wraplength=720, justify="left",
        )
        tip.pack(anchor="w", padx=20, pady=(0, 10))

        filt = ctk.CTkFrame(self, fg_color="transparent")
        filt.pack(anchor="w", fill="x", padx=20, pady=(0, 8))
        self.group_var = ctk.StringVar(value="可能想卸载")
        self.group_seg = ctk.CTkSegmentedButton(
            filt, values=["可能想卸载", "常用软件", "系统组件", "全部"],
            variable=self.group_var, command=lambda _=None: self._render_list(),
        )
        self.group_seg.pack(side="left")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(anchor="w", fill="x", padx=20, pady=(0, 6))

        self.refresh_btn = ctk.CTkButton(top, text="刷新列表", width=90, command=self.on_refresh)
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_list())
        self.search = ctk.CTkEntry(top, placeholder_text="搜索软件名…", textvariable=self.search_var, width=190)
        self.search.pack(side="left", padx=(0, 8))

        self.selall_btn = ctk.CTkButton(top, text="全选本页", width=80, fg_color="gray40",
                                         hover_color="gray30", command=self.on_select_all)
        self.selall_btn.pack(side="left", padx=(0, 8))
        self.clear_btn = ctk.CTkButton(top, text="清空选择", width=80, fg_color="gray40",
                                       hover_color="gray30", command=self.on_clear_sel)
        self.clear_btn.pack(side="left", padx=(0, 8))

        self.uninstall_btn = ctk.CTkButton(top, text="卸载选中", width=110,
                                           fg_color="#b04a3a", hover_color="#933a2c",
                                           command=self.on_uninstall_selected)
        self.uninstall_btn.pack(side="left")

        opt = ctk.CTkFrame(self, fg_color="transparent")
        opt.pack(anchor="w", fill="x", padx=20, pady=(0, 6))
        self.deep_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt, text="彻底卸载（卸载后清理残留文件夹和注册表项）",
                        variable=self.deep_var).pack(side="left", padx=(0, 16))
        self.silent_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt, text="静默卸载（尽量不弹各自的卸载窗口）",
                        variable=self.silent_var).pack(side="left")

        self.status = ctk.CTkLabel(self, text="点【刷新列表】加载已安装软件。", anchor="w",
                                   text_color=("gray30", "gray80"))
        self.status.pack(anchor="w", fill="x", padx=20, pady=(0, 6))

        self.list_box = ctk.CTkScrollableFrame(self, label_text="软件列表（勾选要卸载的）")
        self.list_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _set_status(self, text: str):
        self.status.configure(text=text)
        self.update_idletasks()

    def on_refresh(self):
        if self._busy:
            return
        self._set_status("正在读取已安装软件…")
        self.refresh_btn.configure(state="disabled")

        def worker():
            try:
                apps = uninstaller.list_installed_apps()
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: mbox.showerror("读取失败", str(e)))
                apps = []
            self._apps = apps
            self._check_vars = {a.name: ctk.BooleanVar(value=False) for a in apps}
            n_junk = sum(1 for a in apps if a.group == "可能想卸载")
            n_keep = sum(1 for a in apps if a.group == "常用软件")
            n_sys = sum(1 for a in apps if a.group == "系统组件")
            self.after(0, self._render_list)
            self.after(0, lambda: self.refresh_btn.configure(state="normal"))
            self.after(0, lambda: self._set_status(
                f"共 {len(apps)} 个：可能想卸载 {n_junk}，常用 {n_keep}，系统 {n_sys}。"
            ))

        threading.Thread(target=worker, daemon=True).start()

    def _visible_apps(self):
        keyword = self.search_var.get().strip().lower()
        group_filter = self.group_var.get()
        out = []
        for app in self._apps:
            if keyword and keyword not in app.name.lower():
                continue
            if group_filter != "全部" and app.group != group_filter:
                continue
            out.append(app)
        return out

    def _render_list(self):
        for w in self.list_box.winfo_children():
            w.destroy()

        apps = self._visible_apps()
        if not apps:
            ctk.CTkLabel(
                self.list_box,
                text="（这个分组下没有软件。先点【刷新列表】，或切换到其它分组/全部）",
            ).pack(anchor="w", padx=8, pady=8)
            return

        for app in apps:
            meta = []
            if app.size_mb:
                meta.append(f"{app.size_mb} MB")
            if app.install_date:
                meta.append(f"装于 {app.install_date}")
            if app.version:
                meta.append(f"v{app.version}")
            if app.publisher:
                meta.append(app.publisher)
            if app.is_protected:
                meta.append("系统组件·受保护")
            sub = "  |  ".join(meta)

            row = ctk.CTkFrame(self.list_box, fg_color=("gray90", "gray20"))
            row.pack(fill="x", padx=4, pady=3)
            var = self._check_vars.setdefault(app.name, ctk.BooleanVar(value=False))
            text = app.name + (f"\n{sub}" if sub else "")
            cb = ctk.CTkCheckBox(row, text=text, variable=var)
            cb.pack(anchor="w", fill="x", padx=8, pady=6)

    def on_select_all(self):
        for app in self._visible_apps():
            self._check_vars[app.name].set(True)

    def on_clear_sel(self):
        for var in self._check_vars.values():
            var.set(False)

    def _selected_apps(self):
        names = {n for n, v in self._check_vars.items() if v.get()}
        return [a for a in self._apps if a.name in names]

    def on_uninstall_selected(self):
        if self._busy:
            return
        targets = self._selected_apps()
        if not targets:
            mbox.showinfo("未选择", "请先勾选要卸载的软件。")
            return

        protected = [a.name for a in targets if a.is_protected]
        deep = self.deep_var.get()
        silent = self.silent_var.get()

        warn = f"将卸载选中的 {len(targets)} 个软件：\n" + "、".join(a.name for a in targets[:8])
        if len(targets) > 8:
            warn += f" 等 {len(targets)} 个"
        warn += "\n\n卸载不可逆。"
        if deep:
            warn += "已勾选【彻底卸载】，会一并删除残留文件夹和注册表项。"
        if protected:
            warn += f"\n\n注意：其中 {len(protected)} 个是系统/受保护组件，强烈不建议卸载！"
        warn += "\n\n确定继续吗？"
        if not mbox.askyesno("确认卸载", warn):
            return

        self._busy = True
        self.uninstall_btn.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")

        def worker():
            ok, failed, cleaned = [], [], 0
            total = len(targets)
            for i, app in enumerate(targets, 1):
                self.after(0, lambda i=i, n=app.name: self._set_status(f"正在卸载 {i}/{total}：{n}"))
                res = uninstaller.uninstall(app, deep=deep, silent=silent)
                if res.get("error"):
                    failed.append(f"{app.name}：{res['error']}")
                else:
                    ok.append(app.name)
                    lo = res.get("leftovers")
                    if lo and (lo.get("dir_removed") or lo.get("reg_removed")):
                        cleaned += 1

            def done():
                self._busy = False
                self.uninstall_btn.configure(state="normal")
                self.refresh_btn.configure(state="normal")
                summary = f"完成。成功 {len(ok)} 个，失败 {len(failed)} 个。"
                if deep:
                    summary += f"\n其中清理残留 {cleaned} 个。"
                if failed:
                    summary += "\n\n失败：\n" + "\n".join("· " + x for x in failed[:8])
                self._set_status(summary.replace("\n", " "))
                mbox.showinfo("卸载结果", summary)
                self.on_refresh()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
