"""软件卸载（全部在本工具内完成，不依赖第三方软件）。

- 读取已安装软件列表（含注册表卸载项位置，便于清残留）。
- 普通/静默卸载：调用软件登记的卸载命令。
- 彻底卸载：卸载后再清理残留的安装目录和注册表卸载项（带安全防护）。
- 支持批量（多选）卸载，由界面循环调用。

注意：卸载和清残留需要管理员权限，打包时已要求以管理员身份运行。
"""
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from . import paths

try:
    import winreg  # type: ignore
except ImportError:  # 非 Windows 占位
    winreg = None  # type: ignore

UNINSTALL_KEYS = [
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

# 系统/运行库类关键词：命中即视为不建议卸载
PROTECTED_KEYWORDS = (
    "microsoft windows", "windows sdk", "windows driver kit", "device driver",
    "redistributable", "runtime library", ".net runtime", ".net framework",
    "directx", "visual c++", "vc++ redistributable", "microsoft edge webview",
)

# 常用/需要保留的软件关键词，归入"常用软件"组
KEEP_KEYWORDS = (
    "chrome", "firefox", "edge", "browser", "夸克",
    "office", "word", "excel", "powerpoint", "wps", "钉钉", "腾讯会议", "腾讯文档",
    "飞书", "飞连", "outlook", "foxit", "福昕", "acrobat", "网盘", "zoom", "welink",
    "visual studio", "vscode", "pycharm", "intellij", "idea", "android studio",
    "git", "navicat", "docker", "anaconda", "python", "node", "jdk", "java",
    "cursor", "trae", "datagrip", "webstorm", "goland", "clion",
    "potplayer", "网易云", "qq音乐", "酷狗", "bilibili", "剪映", "premiere",
    "photoshop", "lightroom", "filmora",
    "火绒", "360", "杀毒", "defender", "电脑管家", "驱动",
    "微信", "wechat", "qq", "telegram", "tim",
)


@dataclass
class AppEntry:
    name: str
    publisher: str = ""
    version: str = ""
    size_mb: float = 0.0
    uninstall_string: str = ""
    quiet_uninstall_string: str = ""
    install_location: str = ""
    install_date: str = ""
    is_protected: bool = False
    group: str = ""
    reg_hive: str = ""
    reg_path: str = ""
    reg_wow64: int = 0
    extra: dict = field(default_factory=dict)


def _open_root(root_name: str):
    return winreg.HKEY_LOCAL_MACHINE if root_name == "HKLM" else winreg.HKEY_CURRENT_USER


def _read_value(key, name: str, default=""):
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return value
    except OSError:
        return default


def _judge_protected(name: str, publisher: str) -> bool:
    low_name = (name or "").lower()
    if any(k in low_name for k in PROTECTED_KEYWORDS):
        return True
    low_pub = (publisher or "").lower()
    if "microsoft" in low_pub and ("windows" in low_name or "update" in low_name):
        return True
    return False


def _format_install_date(raw) -> str:
    s = str(raw or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def classify_app_group(app: "AppEntry") -> str:
    if app.is_protected:
        return "系统组件"
    text = f"{app.name} {app.publisher}".lower()
    if any(k in text for k in KEEP_KEYWORDS):
        return "常用软件"
    return "可能想卸载"


def list_installed_apps() -> list[AppEntry]:
    """读取注册表，返回去重后的已安装软件列表。"""
    if winreg is None:
        return []

    found: dict[str, AppEntry] = {}
    for root_name, subkey in UNINSTALL_KEYS:
        wow64 = 0 if "WOW6432Node" in subkey else winreg.KEY_WOW64_64KEY
        try:
            root = _open_root(root_name)
            base = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | wow64)
        except OSError:
            continue

        for i in range(winreg.QueryInfoKey(base)[0]):
            try:
                sub_name = winreg.EnumKey(base, i)
                app_key = winreg.OpenKey(base, sub_name, 0, winreg.KEY_READ | wow64)
            except OSError:
                continue
            with app_key:
                name = _read_value(app_key, "DisplayName")
                if not name:
                    continue
                if _read_value(app_key, "SystemComponent", 0) == 1:
                    continue
                if _read_value(app_key, "ParentKeyName"):
                    continue
                uninstall = _read_value(app_key, "UninstallString")
                quiet = _read_value(app_key, "QuietUninstallString")
                if not uninstall and not quiet:
                    continue
                publisher = _read_value(app_key, "Publisher")
                version = _read_value(app_key, "DisplayVersion")
                size_kb = _read_value(app_key, "EstimatedSize", 0)
                try:
                    size_mb = round(int(size_kb) / 1024, 1)
                except (TypeError, ValueError):
                    size_mb = 0.0
                location = _read_value(app_key, "InstallLocation")
                install_date = _format_install_date(_read_value(app_key, "InstallDate"))

                if name in found:
                    continue
                found[name] = AppEntry(
                    name=name,
                    publisher=publisher,
                    version=version,
                    size_mb=size_mb,
                    uninstall_string=uninstall,
                    quiet_uninstall_string=quiet,
                    install_location=location,
                    install_date=install_date,
                    is_protected=_judge_protected(name, publisher),
                    reg_hive=root_name,
                    reg_path=subkey + "\\" + sub_name,
                    reg_wow64=wow64,
                )

    apps = list(found.values())
    for a in apps:
        a.group = classify_app_group(a)
    group_order = {"可能想卸载": 0, "常用软件": 1, "系统组件": 2}
    apps.sort(key=lambda a: (group_order.get(a.group, 9), a.name.lower()))
    return apps


def _log_action(app_name: str, mode: str, result: str) -> None:
    log_path = os.path.join(paths.get_log_dir(), "uninstall.log")
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{mode}\t{result}\t{app_name}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def _build_uninstall_command(app: AppEntry, silent: bool) -> str | None:
    """构造卸载命令。silent=True 时尽量加静默参数，便于批量无人值守。"""
    base = app.uninstall_string or app.quiet_uninstall_string
    if not base:
        return None
    if not silent:
        return base
    if app.quiet_uninstall_string:
        return app.quiet_uninstall_string

    low = base.lower()
    if "msiexec" in low:
        cmd = base.replace("/I", "/X").replace("/i", "/X")
        if "/qn" not in low and "/quiet" not in low:
            cmd += " /qn /norestart"
        return cmd
    if "unins00" in low:  # Inno Setup 卸载器（unins000.exe）
        return base + " /VERYSILENT /NORESTART /SUPPRESSMSGBOXES"
    # 其余（含 NSIS 的 uninstall.exe）常见支持 /S
    return base + " /S"


def run_uninstall(app: AppEntry, silent: bool = True, timeout: int = 900) -> int:
    """执行卸载命令并等待结束，返回进程退出码（None 视为已启动）。"""
    cmd = _build_uninstall_command(app, silent)
    if not cmd:
        _log_action(app.name, "uninstall", "no_command")
        raise ValueError("该软件未提供卸载命令，无法卸载。")
    try:
        proc = subprocess.run(cmd, shell=True, timeout=timeout)
        _log_action(app.name, "silent" if silent else "normal", f"rc={proc.returncode}")
        return proc.returncode
    except subprocess.TimeoutExpired:
        _log_action(app.name, "uninstall", "timeout")
        raise TimeoutError("卸载超时（可能在等你确认它的窗口），请手动完成或重试。")
    except Exception as e:  # noqa: BLE001
        _log_action(app.name, "uninstall", f"error:{e}")
        raise


# 绝不允许删除的目录（防止误删系统）
def _safe_to_delete_dir(path: str) -> bool:
    if not path:
        return False
    p = os.path.normpath(path)
    if not os.path.isdir(p):
        return False
    low = p.lower().rstrip("\\")
    parts = [x for x in low.split("\\") if x]
    if len(parts) < 2:  # 形如 C:\X 太浅，禁止
        return False
    deny = {
        os.environ.get("SystemRoot", r"C:\Windows").lower().rstrip("\\"),
        r"c:\program files", r"c:\program files (x86)", r"c:\programdata",
        r"c:\users", os.path.expanduser("~").lower().rstrip("\\"),
        r"c:\windows", r"c:\windows\system32",
    }
    if low in deny:
        return False
    return True


def _delete_reg_tree(root, subpath: str, wow64: int) -> bool:
    """递归删除注册表项（卸载项一般无子项，做递归更稳）。"""
    access = winreg.KEY_ALL_ACCESS | wow64
    try:
        key = winreg.OpenKey(root, subpath, 0, access)
    except OSError:
        return False
    try:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_reg_tree(root, subpath + "\\" + child, wow64)
    finally:
        winreg.CloseKey(key)
    try:
        winreg.DeleteKeyEx(root, subpath, wow64, 0)
        return True
    except (OSError, NotImplementedError):
        try:
            winreg.DeleteKey(root, subpath)
            return True
        except OSError:
            return False


def clean_leftovers(app: AppEntry) -> dict:
    """清理残留：安装目录 + 注册表卸载项。带安全防护，绝不碰系统目录。"""
    result = {"dir_removed": False, "reg_removed": False, "notes": []}

    loc = app.install_location
    if loc and os.path.isdir(loc):
        if _safe_to_delete_dir(loc):
            try:
                shutil.rmtree(loc, ignore_errors=False)
                result["dir_removed"] = True
            except Exception as e:  # noqa: BLE001
                result["notes"].append(f"残留目录删除失败：{e}")
        else:
            result["notes"].append("残留目录涉及系统路径，已跳过（安全保护）。")

    if winreg is not None and app.reg_path and app.reg_hive:
        try:
            root = _open_root(app.reg_hive)
            if _delete_reg_tree(root, app.reg_path, app.reg_wow64):
                result["reg_removed"] = True
        except Exception as e:  # noqa: BLE001
            result["notes"].append(f"注册表项删除失败：{e}")

    _log_action(app.name, "clean", f"dir={result['dir_removed']},reg={result['reg_removed']}")
    return result


def uninstall(app: AppEntry, deep: bool = False, silent: bool = True) -> dict:
    """卸载一个软件。

    deep=True 时为"彻底卸载"：先正常卸载，再清理残留目录和注册表项。
    返回结果字典。
    """
    out = {"name": app.name, "returncode": None, "leftovers": None, "error": None}
    try:
        out["returncode"] = run_uninstall(app, silent=silent)
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    if deep:
        out["leftovers"] = clean_leftovers(app)
    return out
