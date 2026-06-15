# OneShot

> 一键直达文献：选中引用文本 → 快捷键 → 自动搜索并下载论文 PDF

基于 Python 3.14+ / pywebview / Vue 3 + Vuetify / AnyStyle (Ruby) 的桌面端学术论文快速下载工具。选中任意格式的论文引用文本，按下快捷键即可自动解析引用、搜索 Semantic Scholar 并下载对应 PDF。

---

## ⚠️ 项目已存档

本项目由于存在诸多问题并且代码架构相当糟糕已停止维护，请移步至新项目：

### 🔗 [OnePot](https://github.com/Raiscies/onepot)

新项目基于 **Pot** 项目重写，修复了本项目的多项问题：

| | OneShot (本项目) | onepot (新项目) |
|---|---|---|
| 框架 | Python + pywebview | Rust + Tauri |
| 窗口边框 | 难以调节大小 | 原生窗口管理 |
| 快捷键 | keyboard 库，修饰键压制问题 | Tauri 原生全局热键 |
| 前后端通信 | 轮询 (_result_version) | Tauri invoke / event |
| 透明窗口 | 不支持 | 原生支持 |

---

## 快速回顾

- 选中论文引用文本 → 按 `` Ctrl+` `` → 自动解析、搜索、下载
- 支持 AnyStyle 解析原始引用格式
- Semantic Scholar 补全文献元数据
- 多出版商 PDF 下载（ACM、IEEE、Springer、Nature、SIAM、Dagstuhl 等）
- CloudflareBypass 代理支持
- 命名模板、自动打开 PDF、限流等配置项
