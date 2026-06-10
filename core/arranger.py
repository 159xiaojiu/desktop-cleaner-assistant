"""整理完成后，把桌面上的分类文件夹图标按固定顺序整齐排列（Win10/11 通用）。"""
from __future__ import annotations

import os
import time

import pythoncom
import win32com.client as wcomcli
from win32com.shell import shell, shellcon

from . import paths
from .classifier import Classifier

IID_IFolderView = "{CDE725B0-CCC9-4519-917E-325D72FAB4CE}"
CLSID_ShellWindows = "{9BA05972-F6A8-11CF-A442-00A0C90A8F39}"
SWC_DESKTOP = 0x08
SWFO_NEEDDISPATCH = 0x01

MARGIN_X = 40
MARGIN_Y = 40
GRID_Y = 80


def _get_folder_view():
    """通过 IFolderView 访问桌面图标（Win11 下 ListView 消息已不可靠）。"""
    pythoncom.CoInitialize()
    shell_windows = wcomcli.Dispatch(CLSID_ShellWindows)
    for _ in range(3):
        dispatch = shell_windows.FindWindowSW(
            wcomcli.VARIANT(pythoncom.VT_I4, shellcon.CSIDL_DESKTOP),
            wcomcli.VARIANT(pythoncom.VT_EMPTY, None),
            SWC_DESKTOP,
            0,
            SWFO_NEEDDISPATCH,
        )
        if dispatch:
            break
        time.sleep(0.3)
    if not dispatch:
        return None, None

    service_provider = dispatch._oleobj_.QueryInterface(pythoncom.IID_IServiceProvider)
    browser = service_provider.QueryService(shell.SID_STopLevelBrowser, shell.IID_IShellBrowser)
    shell_view = browser.QueryActiveShellView()
    folder_view = shell_view.QueryInterface(IID_IFolderView)
    desktop_folder = shell.SHGetDesktopFolder()
    return folder_view, desktop_folder


def _existing_categories_on_desktop(category_order: list[str]) -> list[str]:
    primary = paths.get_primary_desktop()
    existing: set[str] = set()
    try:
        for name in os.listdir(primary):
            if os.path.isdir(os.path.join(primary, name)) and name in category_order:
                existing.add(name)
    except OSError:
        pass
    return [c for c in category_order if c in existing]


def _build_name_to_item(folder_view, desktop_folder) -> dict[str, object]:
    mapping: dict[str, object] = {}
    count = folder_view.ItemCount(shellcon.SVGIO_ALLVIEW)
    for i in range(count):
        item = folder_view.Item(i)
        name = desktop_folder.GetDisplayNameOf([item], shellcon.SHGDN_NORMAL)
        if name and name not in mapping:
            mapping[name] = item
    return mapping


def arrange_category_folders(category_order: list[str] | None = None) -> dict:
    """把分类文件夹图标在主桌面左侧按预设顺序排成一列。"""
    order = category_order or Classifier().categories_order
    targets = _existing_categories_on_desktop(order)
    if not targets:
        return {"ok": True, "arranged": 0, "message": "没有需要排列的分类文件夹。"}

    try:
        folder_view, desktop_folder = _get_folder_view()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "arranged": 0, "message": f"无法访问桌面图标：{exc}"}

    if folder_view is None or desktop_folder is None:
        return {"ok": False, "arranged": 0, "message": "未找到桌面图标区域，排列跳过。"}

    name_to_item = _build_name_to_item(folder_view, desktop_folder)
    arranged = 0
    for row, cat in enumerate(targets):
        item = name_to_item.get(cat)
        if item is None:
            continue
        y = MARGIN_Y + row * GRID_Y
        try:
            folder_view.SelectAndPositionItem(item, (MARGIN_X, y), shellcon.SVSI_POSITIONITEM)
            arranged += 1
        except Exception:  # noqa: BLE001
            continue

    if arranged == 0:
        return {
            "ok": False,
            "arranged": 0,
            "message": "分类文件夹在磁盘上存在，但未在桌面显示为图标，排列跳过。",
        }
    return {
        "ok": True,
        "arranged": arranged,
        "message": f"已按顺序排列 {arranged} 个分类文件夹图标。",
    }
