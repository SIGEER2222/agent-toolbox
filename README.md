# agent-toolbox

AI agent 实操过的工具/流程 runbook 集合。每个子目录一个主题，含可直接复用的脚本与踩坑记录。
本仓库面向 AI 阅读：事实、命令、坑位均按"实测验证过才写"的标准记录。

## 目录

| 子目录 | 主题 |
|---|---|
| [tvbox-video/](tvbox-video/) | TVBox/zyfun 在线点播 + 4K 磁链下载 + B站弹幕转 ASS 本地播放全流程（Windows） |

## 编写约定

- 每个主题目录自带 README.md：步骤 + 命令 + 实测验证方法 + 坑
- 脚本与文档同目录，路径以 `C:\Code\TVbox\` 为例（迁移时全文替换）
- 网络环境备注：本机有 Clash(7897) 系统代理 + WireGuard 隧道，文档标注了哪些流量走代理/直连
