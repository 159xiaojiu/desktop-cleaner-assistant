"""桌面清理小助手 — 程序入口。

直接运行：python app.py        启动图形界面
命令行预览：python app.py --preview   仅打印桌面分类预览（不动文件，便于自测）
"""
import sys


def run_preview():
    import io

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    from core import organizer

    grouped = organizer.preview()
    total = sum(len(v) for v in grouped.values())
    print(f"[预览] 共 {total} 个项目，{len(grouped)} 个类别（不会移动任何文件）：\n")
    for category, items in grouped.items():
        print(f"[{category}] {len(items)} 个")
        for item in items:
            print(f"    - {item.name}")
        print()


def run_gui():
    from ui.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


def main():
    if "--preview" in sys.argv:
        run_preview()
    else:
        run_gui()


if __name__ == "__main__":
    main()
