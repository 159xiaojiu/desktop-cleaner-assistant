"""集中管理路径：桌面位置、应用数据目录、规则文件、第三方目录。"""
import os
import sys


def get_base_dir() -> str:
    """返回程序所在目录。打包成 exe 后用 exe 所在目录，源码运行用项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_base_dir() -> str:
    """返回资源根目录。

    - 源码运行：项目根目录
    - PyInstaller onefile：sys._MEIPASS 临时解包目录
    - 其他 frozen 场景：exe 同目录
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and os.path.isdir(meipass):
            return meipass
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_user_desktop() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")


def get_public_desktop() -> str:
    public = os.environ.get("PUBLIC", r"C:\Users\Public")
    return os.path.join(public, "Desktop")


def get_desktop_roots() -> list[str]:
    """返回需要扫描的桌面根目录（去重、仅保留存在的）。"""
    roots = []
    for path in (get_user_desktop(), get_public_desktop()):
        if path and os.path.isdir(path) and path not in roots:
            roots.append(path)
    return roots


def get_primary_desktop() -> str:
    """整理时分类文件夹只建在这里（用户自己的桌面）。

    Windows 还有「公共桌面」，若两边各建一套「办公/工具」会看起来像重复文件夹。
    因此：扫描两个桌面，但归类目标统一落到用户桌面。
    """
    user = get_user_desktop()
    if os.path.isdir(user):
        return user
    roots = get_desktop_roots()
    return roots[0] if roots else user


def get_app_data_dir() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "桌面清理助手")
    os.makedirs(path, exist_ok=True)
    return path


def get_history_dir() -> str:
    path = os.path.join(get_app_data_dir(), "history")
    os.makedirs(path, exist_ok=True)
    return path


def get_log_dir() -> str:
    path = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def get_rules_path() -> str:
    return os.path.join(get_resource_base_dir(), "data", "rules.json")


def get_bcu_dir() -> str:
    return os.path.join(get_resource_base_dir(), "third_party", "BCUninstaller")
