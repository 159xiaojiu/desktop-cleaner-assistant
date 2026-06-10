"""分类引擎：关键词匹配 -> 扩展名 -> 兜底"其他"。"""
import json
import os

from . import paths
from .scanner import DesktopItem

DEFAULT_RULES = {
    "categories_order": [
        "浏览器", "办公", "开发", "游戏", "社交", "影音",
        "工具", "文档", "图片", "压缩包", "安装包", "其他",
    ],
    "keyword_rules": {},
    "ext_rules": {},
    "fallback_category": "其他",
}


class Classifier:
    def __init__(self, rules: dict | None = None):
        self.rules = rules or self._load_rules()
        self.fallback = self.rules.get("fallback_category", "其他")

    @staticmethod
    def _load_rules() -> dict:
        path = paths.get_rules_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(DEFAULT_RULES)

    @property
    def categories_order(self) -> list[str]:
        return self.rules.get("categories_order", DEFAULT_RULES["categories_order"])

    def classify(self, item: DesktopItem) -> str:
        haystack = self._build_haystack(item)

        keyword_rules = self.rules.get("keyword_rules", {})
        for category in self.categories_order:
            for kw in keyword_rules.get(category, []):
                kw = kw.strip().lower()
                if kw and kw in haystack:
                    return category

        if not item.is_dir and item.ext:
            ext_rules = self.rules.get("ext_rules", {})
            for category, exts in ext_rules.items():
                if item.ext in [e.lower() for e in exts]:
                    return category

        if item.is_dir:
            return self.fallback

        return self.fallback

    @staticmethod
    def _build_haystack(item: DesktopItem) -> str:
        # 只用文件名 + 目标程序的文件名（不含完整路径），
        # 避免把 "...\Programs\..." 之类路径里的字母误当成关键词命中。
        parts = [os.path.splitext(item.name)[0]]
        if item.target:
            parts.append(os.path.splitext(os.path.basename(item.target))[0])
        return " ".join(parts).lower()

    def classify_all(self, items: list[DesktopItem]) -> dict[str, list[DesktopItem]]:
        """返回 {类别: [条目...]}，按 categories_order 排序，空类别不返回。"""
        result: dict[str, list[DesktopItem]] = {}
        for item in items:
            category = self.classify(item)
            result.setdefault(category, []).append(item)
        ordered: dict[str, list[DesktopItem]] = {}
        for category in self.categories_order:
            if category in result:
                ordered[category] = result[category]
        for category, lst in result.items():
            if category not in ordered:
                ordered[category] = lst
        return ordered
