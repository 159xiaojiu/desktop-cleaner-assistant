# 桌面清理小助手 (Desktop Cleaner Assistant)

Windows 桌面整理与软件卸载工具：自动分类桌面图标，并集成 Bulk Crap Uninstaller 卸载顽固软件。

> 完整规格见 [SPEC.md](SPEC.md) · 详细步骤见 [使用说明.md](使用说明.md)

## 适用场景

| 场景 | 功能 |
| --- | --- |
| 桌面图标过多、难以查找 | 按规则自动分类到对应文件夹 |
| 整理前想先确认结果 | 整理前预览，支持一键撤销与历史记录 |
| 普通方式无法卸载的软件 | 强力卸载与残留清理 |

## 功能

**桌面整理**
- 扫描桌面图标 → 预览分类 → 一键整理 → 一键撤销

**软件卸载**
- 列出已安装软件，按常用程度分组
- 支持批量卸载、静默卸载、清理残留

## 快速开始

```powershell
py -m pip install -r requirements.txt
py app.py
```

预览模式（不移动文件）：`py app.py --preview`

## 技术栈

- Python 3.10+ · CustomTkinter
- PyInstaller 打包 · Windows 管理员权限（卸载功能）
- 卸载内核：Bulk Crap Uninstaller

## 目录结构

```
app.py              入口
core/               扫描、分类、整理、卸载逻辑
ui/                 界面
data/rules.json     分类规则
SPEC.md             产品需求与实现规格
```

## 许可证

第三方组件 BCU 遵循其原项目许可证。
