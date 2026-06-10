"""整理执行器：把桌面条目移动到分类文件夹，记录每一步以便一键撤销。

安全要点：
- 永不覆盖：目标重名时自动加后缀 (1)(2)...
- 边移边记录：出错即停，已移动的部分仍可撤销。
- 移动记录保存在 APPDATA（不在桌面），避免被自己整理掉。
"""
import json
import os
import shutil
import time
from datetime import datetime

from . import paths
from .arranger import arrange_category_folders
from .classifier import Classifier
from .scanner import DesktopItem, scan_desktop, match_category_folder


def _safe_move(src: str, dst: str, attempts: int = 3, pause: float = 0.4) -> None:
    """带重试的移动：文件可能被杀毒/OneDrive/系统短暂占用，重试几次更稳。"""
    last_err = None
    for i in range(attempts):
        try:
            shutil.move(src, dst)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(pause * (i + 1))
    raise last_err  # type: ignore[misc]


def _unique_destination(dest_dir: str, name: str) -> tuple[str, bool]:
    """返回不冲突的目标完整路径，以及是否发生了重命名。"""
    target = os.path.join(dest_dir, name)
    if not os.path.exists(target):
        return target, False
    base, ext = os.path.splitext(name)
    i = 1
    while True:
        candidate = os.path.join(dest_dir, f"{base}({i}){ext}")
        if not os.path.exists(candidate):
            return candidate, True
        i += 1


def _is_already_in_category(item: DesktopItem, category: str) -> bool:
    """条目是否已在主桌面的正确分类文件夹里。"""
    primary = paths.get_primary_desktop()
    dest_dir = os.path.normcase(os.path.join(primary, category))
    parent = os.path.normcase(os.path.dirname(item.path))
    return parent == dest_dir


def _consolidate_category_folders(category_names: set[str]) -> int:
    """把各桌面（含公共桌面、办公(1) 等重复壳）里的分类内容合并到主桌面唯一文件夹。"""
    primary = paths.get_primary_desktop()
    canonical = {cat: os.path.join(primary, cat) for cat in category_names}
    for dest in canonical.values():
        os.makedirs(dest, exist_ok=True)

    merged = 0
    for root in paths.get_desktop_roots():
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            cat = match_category_folder(name, category_names)
            if not cat:
                continue
            src_dir = os.path.join(root, name)
            if not os.path.isdir(src_dir):
                continue
            dest_dir = canonical[cat]
            if os.path.normcase(os.path.abspath(src_dir)) == os.path.normcase(os.path.abspath(dest_dir)):
                continue
            try:
                for inner in os.listdir(src_dir):
                    inner_src = os.path.join(src_dir, inner)
                    dest, _ = _unique_destination(dest_dir, inner)
                    if os.path.abspath(inner_src) != os.path.abspath(dest):
                        _safe_move(inner_src, dest)
                        merged += 1
            except OSError:
                pass
            try:
                if os.path.isdir(src_dir) and not os.listdir(src_dir):
                    os.rmdir(src_dir)
            except OSError:
                pass
    return merged


def _cleanup_empty_category_folders(category_names: set[str]) -> int:
    """删除所有桌面上已空的分类文件夹（含 办公(1) 这类重复壳）。"""
    removed = 0
    for root in paths.get_desktop_roots():
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            if match_category_folder(name, category_names) is None:
                continue
            full = os.path.join(root, name)
            try:
                if os.path.isdir(full) and not os.listdir(full):
                    os.rmdir(full)
                    removed += 1
            except OSError:
                pass
    return removed


def preview(rules: dict | None = None) -> dict[str, list[DesktopItem]]:
    """只读：返回 {类别: [条目...]} 的整理预览，不动任何文件。"""
    classifier = Classifier(rules)
    category_names = set(classifier.categories_order)
    items = scan_desktop(category_folders=category_names)
    return classifier.classify_all(items)


def organize(progress_cb=None, rules: dict | None = None) -> dict:
    """执行整理。progress_cb(done, total, name) 可选回调用于界面进度。

    返回本次整理的记录字典（已写盘）。
    """
    classifier = Classifier(rules)
    category_names = set(classifier.categories_order)

    # 先把公共桌面 / 重复壳文件夹里的内容合并到主桌面，避免「两个办公」
    merged = _consolidate_category_folders(category_names)

    grouped = preview(rules)

    flat: list[tuple[str, DesktopItem]] = []
    for category, lst in grouped.items():
        for item in lst:
            flat.append((category, item))

    total = len(flat)
    task_id = "move_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    record = {
        "task_id": task_id,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "desktop_roots": paths.get_desktop_roots(),
        "primary_desktop": paths.get_primary_desktop(),
        "merged_from_other_desktops": merged,
        "moves": [],
        "failures": [],
        "status": "running",
    }
    record_path = os.path.join(paths.get_history_dir(), task_id + ".json")

    done = 0
    for category, item in flat:
        done += 1
        try:
            if _is_already_in_category(item, category):
                continue
            dest_dir = os.path.join(item.root, category)
            os.makedirs(dest_dir, exist_ok=True)
            dest, renamed = _unique_destination(dest_dir, item.name)
            if os.path.abspath(item.path) == os.path.abspath(dest):
                continue
            _safe_move(item.path, dest)
            record["moves"].append({
                "name": item.name,
                "category": category,
                "from": item.path,
                "to": dest,
                "renamed": renamed,
            })
        except Exception as e:  # noqa: BLE001
            record["failures"].append({"name": item.name, "reason": str(e)})
        if progress_cb:
            progress_cb(done, total, item.name)

    # 整理完成后清掉变空的分类文件夹
    record["removed_empty_dirs"] = _cleanup_empty_category_folders(category_names)
    # 把分类文件夹图标在主桌面按顺序排整齐
    record["arrange"] = arrange_category_folders(list(category_names))
    record["status"] = "done"
    _write_record(record_path, record)
    return record


def _write_record(path: str, record: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def list_records() -> list[dict]:
    """返回所有整理记录（按时间倒序）的摘要。"""
    history_dir = paths.get_history_dir()
    records = []
    for name in os.listdir(history_dir):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(history_dir, name), "r", encoding="utf-8") as f:
                data = json.load(f)
            records.append(data)
        except Exception:
            continue
    records.sort(key=lambda r: r.get("time", ""), reverse=True)
    return records


def latest_revertable_record() -> dict | None:
    for rec in list_records():
        if rec.get("status") == "done" and rec.get("moves"):
            return rec
    return None


def undo(record: dict | None = None, progress_cb=None) -> dict:
    """撤销一次整理：按记录逆序把文件移回原位。

    返回结果统计 {restored, skipped, conflicts}。
    """
    if record is None:
        record = latest_revertable_record()
    if not record:
        raise ValueError("没有可撤销的整理记录。")

    moves = list(reversed(record.get("moves", [])))
    total = len(moves)
    restored = 0
    conflicts = 0
    done = 0

    for mv in moves:
        src = mv["to"]
        dst = mv["from"]
        if not os.path.exists(src):
            done += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            dst, _ = _unique_destination(os.path.dirname(dst), os.path.basename(dst))
            conflicts += 1
        _safe_move(src, dst)
        restored += 1
        done += 1
        if progress_cb:
            progress_cb(done, total, mv["name"])

    # 撤销后清掉变空的分类文件夹，让桌面回到整理前的样子
    category_names = set(Classifier().categories_order)
    removed_dirs = _cleanup_empty_category_folders(category_names)

    record["status"] = "reverted"
    task_id = record.get("task_id")
    if task_id:
        _write_record(os.path.join(paths.get_history_dir(), task_id + ".json"), record)

    return {
        "restored": restored,
        "skipped": total - restored,
        "conflicts": conflicts,
        "removed_dirs": removed_dirs,
    }
