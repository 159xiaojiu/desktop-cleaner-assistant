"""环境自检：检查依赖、管理员权限、历史目录可写性等。"""
from __future__ import annotations

import importlib
import os
import sys

from . import paths


def _check_admin() -> tuple[bool, str]:
    if os.name != "nt":
        return True, "非 Windows 环境，跳过管理员权限检查。"
    try:
        import ctypes

        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as e:  # noqa: BLE001
        return False, f"无法检测管理员权限：{e}"
    if is_admin:
        return True, "已使用管理员权限运行。"
    return False, "当前不是管理员权限。涉及卸载/清残留时建议右键“以管理员身份运行”。"


def _check_import(mod_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(mod_name)
        return True, f"{mod_name} 可用"
    except Exception as e:  # noqa: BLE001
        return False, f"{mod_name} 不可用：{e}"


def _check_history_writable() -> tuple[bool, str]:
    history = paths.get_history_dir()
    test_file = os.path.join(history, ".write_test.tmp")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        return True, f"历史记录目录可写：{history}"
    except Exception as e:  # noqa: BLE001
        return False, f"历史记录目录不可写：{history}，错误：{e}"


def run_healthcheck() -> list[dict]:
    """返回结构化检查结果列表。"""
    checks: list[dict] = []
    checks.append({"name": "Python版本", "ok": sys.version_info >= (3, 10), "detail": f"{sys.version.split()[0]}"})
    checks.append({"name": "依赖 customtkinter", **_to_dict(_check_import("customtkinter"))})
    checks.append({"name": "依赖 win32com", **_to_dict(_check_import("win32com.client"))})
    checks.append({"name": "管理员权限", **_to_dict(_check_admin())})
    checks.append({"name": "历史目录可写", **_to_dict(_check_history_writable())})
    return checks


def _to_dict(result: tuple[bool, str]) -> dict:
    return {"ok": result[0], "detail": result[1]}

