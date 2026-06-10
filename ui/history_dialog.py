"""整理历史记录弹窗：查看每次整理详情，选择某次撤销。"""
import tkinter.messagebox as mbox

import customtkinter as ctk

from core import organizer


class HistoryDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("整理历史记录")
        self.geometry("620x480")
        self.transient(master)
        self.grab_set()

        tip = ctk.CTkLabel(
            self,
            text="每次「一键整理」都会自动保存记录。可选某次点【撤销此记录】还原到整理前。",
            text_color=("gray40", "gray70"), wraplength=580, justify="left",
        )
        tip.pack(anchor="w", padx=16, pady=(14, 8))

        self.list_box = ctk.CTkScrollableFrame(self, label_text="历史记录（新 → 旧）")
        self.list_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkButton(self, text="关闭", width=100, command=self.destroy).pack(pady=(0, 14))

        self._load()

    def _load(self):
        for w in self.list_box.winfo_children():
            w.destroy()
        records = organizer.list_records()
        if not records:
            ctk.CTkLabel(self.list_box, text="（暂无历史记录）").pack(anchor="w", padx=8, pady=8)
            return

        for rec in records:
            self._add_row(rec)

    def _add_row(self, rec: dict):
        status = rec.get("status", "?")
        moves = len(rec.get("moves", []))
        fails = len(rec.get("failures", []))
        merged = rec.get("merged_from_other_desktops", 0)
        status_txt = {"done": "已完成", "reverted": "已撤销", "running": "进行中"}.get(status, status)
        line1 = f"{rec.get('time', '?')}  |  {status_txt}  |  移动 {moves} 个"
        if fails:
            line1 += f"  |  跳过 {fails} 个"
        if merged:
            line1 += f"  |  合并重复夹 {merged} 个"

        row = ctk.CTkFrame(self.list_box, fg_color=("gray92", "gray22"))
        row.pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(row, text=line1, anchor="w", justify="left").pack(
            anchor="w", fill="x", padx=10, pady=(8, 4),
        )

        btn_row = ctk.CTkFrame(row, fg_color="transparent")
        btn_row.pack(anchor="w", padx=10, pady=(0, 8))

        if status == "done" and moves > 0:
            ctk.CTkButton(
                btn_row, text="撤销此记录", width=100, height=28,
                fg_color="#6a5030", hover_color="#5a4028",
                command=lambda r=rec: self._undo_one(r),
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="查看明细", width=90, height=28,
            fg_color="gray40", hover_color="gray30",
            command=lambda r=rec: self._show_detail(r),
        ).pack(side="left")

    def _show_detail(self, rec: dict):
        moves = rec.get("moves", [])
        fails = rec.get("failures", [])
        lines = [f"时间：{rec.get('time')}", f"状态：{rec.get('status')}", f"移动：{len(moves)} 个"]
        if fails:
            lines.append(f"跳过：{len(fails)} 个")
        if moves:
            lines.append("\n移动明细（前 15 条）：")
            for m in moves[:15]:
                lines.append(f"  · {m.get('name')} → {m.get('category')}")
            if len(moves) > 15:
                lines.append(f"  …共 {len(moves)} 条")
        if fails:
            lines.append("\n跳过明细：")
            for f in fails[:8]:
                lines.append(f"  · {f.get('name')}：{str(f.get('reason', ''))[:50]}")
        mbox.showinfo("记录明细", "\n".join(lines), parent=self)

    def _undo_one(self, rec: dict):
        if not mbox.askyesno(
            "确认撤销",
            f"将撤销 {rec.get('time')} 的整理，把文件移回原位。\n是否继续？",
            parent=self,
        ):
            return
        try:
            result = organizer.undo(rec)
        except Exception as e:  # noqa: BLE001
            mbox.showerror("撤销失败", str(e), parent=self)
            return
        msg = f"已还原 {result['restored']} 个项目。"
        if result.get("removed_dirs"):
            msg += f"\n已清理 {result['removed_dirs']} 个空分类文件夹。"
        mbox.showinfo("撤销完成", msg, parent=self)
        self._load()
