"""扫描桌面上的图标/文件，过滤掉系统特殊项。

只读操作：本模块绝不移动或删除任何文件。
"""
import os
import re
import sys
from dataclasses import dataclass

from . import paths


def _looks_like_own_project(dir_path: str) -> bool:
    """判断某文件夹是不是本工具自己的项目目录（含 app.py + core/uninstaller.py），
    是的话整理时跳过，避免把工具自己埋进分类文件夹里。"""
    try:
        return os.path.isfile(os.path.join(dir_path, "app.py")) and os.path.isfile(
            os.path.join(dir_path, "core", "uninstaller.py")
        )
    except Exception:
        return False


def _self_paths() -> set[str]:
    """本程序自身相关路径（运行中的 exe、源码根目录），整理时必须跳过，
    否则会去移动正在运行的自己导致失败。"""
    result: set[str] = set()
    try:
        result.add(os.path.normcase(os.path.abspath(sys.executable)))
    except Exception:
        pass
    try:
        result.add(os.path.normcase(os.path.abspath(paths.get_base_dir())))
    except Exception:
        pass
    return result

SYSTEM_ITEM_NAMES = {
    "此电脑", "这台电脑", "我的电脑", "this pc", "computer",
    "回收站", "recycle bin",
    "网络", "network",
    "控制面板", "control panel",
    "用户的文件", "用户文件",
}

SYSTEM_EXTS = {".lnk_systemignore"}

DESKTOP_INI = "desktop.ini"


def match_category_folder(name: str, category_folders: set[str]) -> str | None:
    """判断文件夹名是否为分类文件夹（含 办公(1) 这类重复壳）。"""
    if name in category_folders:
        return name
    m = re.match(r"^(.+)\(\d+\)$", name)
    if m and m.group(1) in category_folders:
        return m.group(1)
    return None


@dataclass
class DesktopItem:
    name: str
    path: str
    root: str
    is_dir: bool
    ext: str
    target: str = ""


def _is_system_item(name: str) -> bool:
    base = os.path.splitext(name)[0].strip().lower()
    if name.lower() == DESKTOP_INI:
        return True
    if name.startswith("."):
        return True
    if name.startswith("~$"):  # Office 打开文档时的临时锁文件
        return True
    return base in SYSTEM_ITEM_NAMES


def _resolve_shortcut_target(path: str) -> str:
    """尝试解析 .lnk 快捷方式指向的目标，失败返回空字符串。

    注意：解析完必须显式释放 COM 对象并 gc，否则会短暂占用该 .lnk 文件句柄，
    导致紧接着的"移动"报"文件正被占用"，这正是之前部分快捷方式整理失败的原因。
    """
    if not path.lower().endswith(".lnk"):
        return ""
    shell = None
    shortcut = None
    try:
        import win32com.client  # type: ignore

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(path)
        return shortcut.TargetPath or ""
    except Exception:
        return ""
    finally:
        del shortcut
        del shell


def _append_item(items: list[DesktopItem], seen: set[str], root: str, name: str, full: str) -> None:
    if full in seen:
        return
    if _is_system_item(name):
        return
    if os.path.normcase(os.path.abspath(full)) in _self_paths():
        return
    is_dir = os.path.isdir(full)
    if is_dir and _looks_like_own_project(full):
        return
    ext = "" if is_dir else os.path.splitext(name)[1].lower()
    items.append(
        DesktopItem(
            name=name,
            path=full,
            root=root,
            is_dir=is_dir,
            ext=ext,
            target="",
        )
    )
    seen.add(full)


def find_category_dirs(category_folders: set[str]) -> dict[str, list[str]]:
    """查找桌面上已存在的分类文件夹 {类别名: [完整路径, ...]}（用户桌面 + 公共桌面）。"""
    found: dict[str, list[str]] = {}
    for root in paths.get_desktop_roots():
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for name in entries:
            if name not in category_folders:
                continue
            full = os.path.join(root, name)
            if os.path.isdir(full):
                found.setdefault(name, []).append(full)
    return found


def scan_desktop(category_folders: set[str] | None = None) -> list[DesktopItem]:
    """扫描用户桌面 + 公共桌面，返回可整理条目。

    所有条目的 root 统一为用户桌面（分类文件夹只建一套，避免「两个办公」）。
    """
    category_folders = category_folders or set()
    primary = paths.get_primary_desktop()
    items: list[DesktopItem] = []
    seen_paths: set[str] = set()

    for root in paths.get_desktop_roots():
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for name in entries:
            full = os.path.join(root, name)
            cat = match_category_folder(name, category_folders) if os.path.isdir(full) else None
            if cat:
                try:
                    for inner in os.listdir(full):
                        inner_full = os.path.join(full, inner)
                        _append_item(items, seen_paths, primary, inner, inner_full)
                except OSError:
                    pass
                continue
            _append_item(items, seen_paths, primary, name, full)

    return items
