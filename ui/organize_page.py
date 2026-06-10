"""桌面整理页：扫描预览 -> 一键整理 -> 一键撤销。"""
import threading
import tkinter.messagebox as mbox

import customtkinter as ctk

from core import organizer
from core.arranger import arrange_category_folders
from .history_dialog import HistoryDialog


class OrganizePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._grouped = {}
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="桌面整理", font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(18, 4))

        tip = ctk.CTkLabel(
            self,
            text="先点【扫描预览】看分类结果（不动文件），满意再【一键整理】。"
                 "整理后会自动把分类文件夹在桌面左侧按顺序排整齐。"
                 "不满意可用【一键撤销】或【历史记录】还原。",
            text_color=("gray40", "gray70"),
            wraplength=720,
            justify="left",
        )
        tip.pack(anchor="w", padx=20, pady=(0, 12))

        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(anchor="w", padx=20, pady=(0, 10))

        self.scan_btn = ctk.CTkButton(btn_bar, text="① 扫描预览", width=130, command=self.on_scan)
        self.scan_btn.pack(side="left", padx=(0, 10))

        self.organize_btn = ctk.CTkButton(
            btn_bar, text="② 一键整理", width=130, state="disabled", command=self.on_organize
        )
        self.organize_btn.pack(side="left", padx=(0, 10))

        self.undo_btn = ctk.CTkButton(
            btn_bar, text="↩ 一键撤销", width=130, fg_color="gray40",
            hover_color="gray30", command=self.on_undo
        )
        self.undo_btn.pack(side="left", padx=(0, 10))

        self.history_btn = ctk.CTkButton(
            btn_bar, text="📋 历史记录", width=130, fg_color="#4a5568",
            hover_color="#3d4654", command=self.on_history,
        )
        self.history_btn.pack(side="left", padx=(0, 10))

        self.arrange_btn = ctk.CTkButton(
            btn_bar, text="⇅ 排列图标", width=130, fg_color="#3a5a7a",
            hover_color="#2f4a66", command=self.on_arrange,
        )
        self.arrange_btn.pack(side="left")

        self.status = ctk.CTkLabel(self, text="准备就绪。", anchor="w", text_color=("gray30", "gray80"))
        self.status.pack(anchor="w", fill="x", padx=20, pady=(0, 6))

        self.preview_box = ctk.CTkScrollableFrame(self, label_text="分类预览")
        self.preview_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _set_status(self, text: str):
        self.status.configure(text=text)
        self.update_idletasks()

    def _clear_preview(self):
        for w in self.preview_box.winfo_children():
            w.destroy()

    def on_scan(self):
        self._set_status("正在扫描桌面…")
        self._clear_preview()
        try:
            self._grouped = organizer.preview()
        except Exception as e:  # noqa: BLE001
            mbox.showerror("扫描失败", str(e))
            self._set_status("扫描失败。")
            return

        total = sum(len(v) for v in self._grouped.values())
        if total == 0:
            self._set_status("桌面很干净，没有需要整理的图标。")
            self.organize_btn.configure(state="disabled")
            ctk.CTkLabel(self.preview_box, text="（没有可整理的项目）").pack(anchor="w", padx=8, pady=8)
            return

        for category, items in self._grouped.items():
            header = ctk.CTkLabel(
                self.preview_box,
                text=f"📁 {category}（{len(items)}）",
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            )
            header.pack(anchor="w", fill="x", padx=8, pady=(10, 2))
            for item in items:
                ctk.CTkLabel(
                    self.preview_box, text=f"    • {item.name}", anchor="w",
                    text_color=("gray30", "gray75"),
                ).pack(anchor="w", fill="x", padx=8)

        self.organize_btn.configure(state="normal")
        self._set_status(f"扫描完成：共 {total} 个项目，将分到 {len(self._grouped)} 个类别。")

    def on_organize(self):
        if not self._grouped:
            return
        total = sum(len(v) for v in self._grouped.values())
        if not mbox.askyesno("确认整理", f"将把桌面上的 {total} 个项目移动到分类文件夹。\n整理后可一键撤销。是否继续？"):
            return

        self.scan_btn.configure(state="disabled")
        self.organize_btn.configure(state="disabled")
        self._set_status("正在整理…")

        def worker():
            def progress(done, total_, name):
                self._set_status(f"整理中 {done}/{total_}：{name}")

            try:
                record = organizer.organize(progress_cb=progress)
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: mbox.showerror("整理失败", f"已整理的部分可用撤销还原。\n错误：{e}"))
                self.after(0, lambda: self._set_status("整理失败。"))
            else:
                moved = len(record.get("moves", []))
                failures = record.get("failures", [])
                msg = f"整理完成，移动了 {moved} 个项目。"
                if failures:
                    lines = []
                    for f in failures[:6]:
                        reason = f.get("reason", "")
                        short = "无权限" if "WinError 5" in reason or "Permission" in reason else (
                            "正在使用" if "WinError 32" in reason or "being used" in reason else reason[:40]
                        )
                        lines.append(f"  · {f['name']}（{short}）")
                    more = f"\n  …等共 {len(failures)} 个" if len(failures) > 6 else ""
                    msg += f"\n有 {len(failures)} 个被跳过：\n" + "\n".join(lines) + more
                    msg += "\n\n提示：被占用的请关掉对应软件后重试；无权限的请用管理员身份运行。"
                arrange = record.get("arrange") or {}
                if arrange.get("arranged"):
                    msg += f"\n\n{align.get('message', '已排列分类文件夹图标。')}"
                elif arrange.get("message") and not arrange.get("ok"):
                    msg += f"\n\n排列提示：{arrange.get('message')}"
                self.after(0, lambda: self._set_status(f"整理完成：移动 {moved} 个，跳过 {len(failures)} 个。"))
                self.after(0, self._clear_preview)
                self.after(0, lambda m=msg: mbox.showinfo("完成", m))
            finally:
                self.after(0, lambda: self.scan_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def on_history(self):
        HistoryDialog(self.winfo_toplevel())

    def on_arrange(self):
        self._set_status("正在排列桌面分类文件夹…")
        try:
            result = arrange_category_folders()
        except Exception as e:  # noqa: BLE001
            mbox.showerror("排列失败", str(e))
            self._set_status("排列失败。")
            return
        self._set_status(result.get("message", "排列完成。"))
        mbox.showinfo("排列完成", result.get("message", "完成。"))

    def on_undo(self):
        record = organizer.latest_revertable_record()
        if not record:
            mbox.showinfo("无可撤销", "没有找到可撤销的整理记录。")
            return
        if not mbox.askyesno("确认撤销", f"将撤销 {record.get('time')} 的那次整理，把文件移回原位。是否继续？"):
            return

        self._set_status("正在撤销…")

        def worker():
            try:
                result = organizer.undo(record)
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: mbox.showerror("撤销失败", str(e)))
                self.after(0, lambda: self._set_status("撤销失败。"))
            else:
                msg = f"已还原 {result['restored']} 个项目。"
                if result["conflicts"]:
                    msg += f"（{result['conflicts']} 个因重名已加后缀）"
                if result.get("removed_dirs"):
                    msg += f"\n已清理 {result['removed_dirs']} 个空分类文件夹。"
                self.after(0, lambda: self._set_status(msg.replace("\n", " ")))
                self.after(0, lambda m=msg: mbox.showinfo("撤销完成", m))

        threading.Thread(target=worker, daemon=True).start()
