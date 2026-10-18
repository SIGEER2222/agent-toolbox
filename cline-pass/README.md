# cline-pass Cline Pass 订阅、API key 与 CLI 配置

## 概述

订阅 Cline 官方 ClinePass（$9.99/月的开源权重模型包月），用 KOL 80 折扣码把首月压到约 $2.12 / ¥14.74；拿到 API key 后配 cline CLI 与任意 OpenAI 兼容客户端；并记录了收银台报错与上游路由的实测坑。

## 环境前提

- OS：Windows（浏览器 + npm）；WSL 亦可调 Windows 侧工具
- 依赖：浏览器（登录 app.cline.bot）、Visa/Mastercard/银联卡（**借记卡**，或已开通在线支付的信用卡）、`npm i -g cline`
- 账号：app.cline.bot 注册（Google/GitHub/Microsoft/邮箱均可）

## 操作步骤

### 1. 带码进收银台

普通订阅页没有输码入口，必须走 promo 链接：

```text
https://app.cline.bot/promo?code=TAPAS80
```

80 结尾的码是 KOL 批次码，效果相同（首月 ~80% off），旧码会过期、新码持续放出。登录后自动跳到 Checkout（Stripe 嵌入 iframe）。

预期：收银台显示「订阅 Cline Pass ¥14.74 / 然后从下个月开始每月 ¥73.72」，币种可切 CNY/USD。

### 2. 填支付信息并付款

卡号、有效期、CVC、持卡人姓名、账单地址（国家选中国后填省/市/区/地址行/邮编）。

预期：点「订阅」后无报错跳回 dashboard，Subscription 页显示 "You're subscribed to ClinePass"。

### 3. 建 API key

Dashboard → Account → **API Keys** 标签 → Create API Key → 起名 → 弹窗里复制完整 `sk_...`（只显示一次）。

保存方式（任选，推荐文件最稳）：

```powershell
# Windows 用户环境变量（已开的进程读不到，要新开终端）
[Environment]::SetEnvironmentVariable("CLINE_API_KEY", "sk_...", "User")
```

```bash
# 或写到 key 文件（本 runbook 脚本与 CLI 之外的通用回退）
echo 'sk_...' > ~/.cline_api_key
```

### 4. 配 cline CLI

```bash
npm i -g cline
cline -P cline-pass -k "sk_..." -m "cline-pass/deepseek-v4.1-flash" "Reply with exactly: OK"
```

`-k` 会把 key 存为该 provider 的默认 key；`~/.cline/data/settings/providers.json` 记录 `lastUsedProvider=cline-pass`，之后裸 `cline` 即用订阅模型。换模型用 `-m cline-pass/glm-5.3` 等。

### 5. （可选）取消自动续费

Dashboard → Subscription → Cancel Subscription → 确认对话框「Cancel subscription」。状态变 CANCELLATION SCHEDULED，当期权益保留到月末，页面可随时 Resume Subscription。

## 验证方法

```bash
# API 直连（OpenAI 兼容，模型名必须带 cline-pass/ 前缀）
python scripts/clinepass_call.py --model cline-pass/deepseek-v4.1-flash --prompt "Reply with exactly: OK"
```

期望：stdout 输出 `OK`，stderr meta 里 `model` 形如 `vmc/deepseek-v4p1-flash-contributor-fallbacks`。

```bash
# CLI
cline -P cline-pass -m cline-pass/glm-5.3 "Reply with exactly: OK"
```

期望：输出 `OK`；providers.json 中 `lastUsedProvider` 为 `cline-pass`。

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| Stripe 报「您的信用卡不支持这种购物类型，请尝试用借记卡支付」 | 卡的在线/跨境支付未开通（不是卡组织不支持） | 在发卡侧开通在线支付即可，同张卡可直接过 `[实测 2026-10-18]` |
| 请求被按量计费扣 credits | 模型名没写 `cline-pass/` 前缀 | model 字段写全 `cline-pass/<model>` `[实测]` |
| 解析响应取不到 choices | 响应包了一层 `{"data":{...},"success":true}` 信封 | 取 `resp["data"]["choices"]` `[实测 2026-10-18]` |
| 想固定「官方上游」但无效 | 当前 ds-v4.1-flash/glm-5.3 只有 `openai-compatible-private` 单通道（`fallbacksAvailable:[]`），`providerOptions.gateway.only`/`provider.only` 均被静默忽略 | 无可选上游，不用配；linux.sb 钉上游攻略已过时 `[实测 2026-10-18]` |
| 脚本读不到刚 setx 的 CLINE_API_KEY | 已启动进程的 env block 是旧的 | 新开终端，或读 `~/.cline_api_key` 文件 `[实测]` |
| 收银台看不到优惠 | 从普通订阅页进，没有 promo code 入口 | 必须走 `app.cline.bot/promo?code=` 链接 `[实测]` |
| 计费限额疑惑 | 按 5h 滚动/每周/每月三窗，月窗≈5h×5（API 等价 ~$50），便宜模型高缓存命中下月可用到数 B tokens | dashboard Subscription 页看三窗百分比 `[社区+实测]` |
| WSL 里跑 cline/node 输出坏 | Windows node.exe 在 WSL stdio 损坏 | 走 wsl-windows-interop 册子的 winnode/winps 桥 `[实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/clinepass_call.py | OpenAI 兼容直连封装：env→`~/.cline_api_key` 回退取 key、解信封、打印 provider_metadata 路由、`--probe` 探测 pin 管线 |
