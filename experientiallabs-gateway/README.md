# experientiallabs-gateway Experiential Labs 网关：$1 验证、API key 与模型调用

## 概述

platform.experientiallabs.ai 是 OpenAI 兼容的多模型推理网关（公开目录 1100+ 模型，单 key 实测可调 318 个）。一次性 $1.00 卡验证即解锁：500 credits/月免费档 + 免费/促销模型 + 充值通道。$1 实扣计入余额（1 credit = 1¢）。

## 环境前提

- OS：Windows（浏览器）；调用端任意能发 HTTPS 的环境
- 账号：platform.experientiallabs.ai（Google/GitHub/邮箱注册）
- 支付：Visa/MC/银联卡（借记或已开在线支付的信用卡；部分卡会走发卡行 3DS 短信验证）

## 关键端点

- 推理：`https://api.experientiallabs.ai/v1`（OpenAI Chat Completions / Responses / Messages / Embeddings）
- 管理：`https://api.experientiallabs.ai/api`；模型目录 `GET /api/models` 无需 key
- key 形如 `xpl_` + 40 位小写 hex，只在创建时显示一次，`Authorization: Bearer` 发送

## 操作步骤

### 1. 验证充值 $1

Credits 页 → "Verify with $1.00" → 弹窗选「银行卡」→ Stripe iframe 内填卡号/有效期/CVC → 账单国家切「中国」（邮编栏自动消失）→ **取消 Link 快捷支付勾选** → Pay。

预期：可能跳发卡行 3DS 页（银联 acspage.cupdapp.cn，选语言→短信动态码到预留手机）→ 完成后 Credits 余额 600（= 500 免费月额 + 100 充值）。

### 2. 建 API key

API Keys → Create key → 起名（如 devin-cli）→ Monthly budget 留空（No cap）→ 弹窗复制 `xpl_...`。

保存：

```bash
echo 'xpl_...' > ~/.explabs_api_key        # 或 export EXPLABS_API_KEY=xpl_...
```

### 3. 调用

```bash
python scripts/expl_call.py --model deepseek-v4.1-flash --prompt "Say OK"
# 或裸 curl：
curl https://api.experientiallabs.ai/v1/chat/completions \
  -H "Authorization: Bearer xpl_..." -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4.1-flash","messages":[{"role":"user","content":"hi"}]}'
```

## 验证方法

```bash
curl -s https://api.experientiallabs.ai/v1/models -H "Authorization: Bearer xpl_..." | head -c 100
```

期望：HTTP 200，`{"object":"list","data":[...]}`；本 key 实测返回 318 个模型 `[实测 2026-10-18]`。

调用验证：`choices[0].message.content` 非空、`usage.cost` 为 USD 实扣、`provider` 形如 `experiential_cloud`。Credits 页余额实时可见，pending 调用稍后才结算。

### 中国 IP 可用性矩阵（[实测 2026-10-18]）

| 状态 | 模型 |
|---|---|
| ✅ 可调 | deepseek-v4.1-flash（~$0.3/1M）、**deepseek-v4.1-flash-uncensored（cost 实测为 0，免费）**、kimi-k3、glm-5.3 / glm-5.3-flash、qwen3.8-max、minimax-m3 |
| ❌ 403 `model_location_not_supported` | claude-sonnet-5、gpt-6-sol、gpt-6-luna、gemini-3.8-flash（美系模型按 DB-IP 地理校验，全线封） |
| ❌ 429 `model_requires_purchase` | mimo-v2.5-pro（$1 验证不算 purchase，需先买 credits 解锁） |
| ❌ 503 route unavailable | gpt-6-luna-decisions、clef-flash、jev-latest（路由暂不可用） |

结论：中国 IP 只能调中系/开源模型；要全目录需非受限地区出口 `[需验证：代理出口是否解锁]`。

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| Pay 按钮始终灰色 | Stripe 表单里 **Link 快捷支付勾选框默认选中**，把邮箱/手机号变必填 | `input[name="linkOptIn"]` uncheck `[实测 2026-10-18]` |
| 邮编只填进 5 位 | 账单国家默认 US，邮编栏是美国格式限 5 位 | 国家切 CN 后邮编栏直接消失 `[实测]` |
| 支付卡半天无响应 | 发卡行 3DS challenge 弹在 `stripe-challenge-frame` iframe（兴业等走 acspage.cupdapp.cn） | 完成短信动态码验证 `[实测]` |
| 402/余额不足于免费模型 | 未做 $1 验证，credits=0 | Verify with $1.00（实扣入余额，非预授权）`[实测]` |
| `GET /v1/models` 401 invalid_key | key 为空/未生效（新建 key 有传播延迟可能）；注意 key 只在创建弹窗出现一次 | 确认 `xpl_`+40hex 完整；文件存 CRLF 行尾读取注意 strip `[实测]` |
| 自动化时 `$` 被 shell 层吃掉 | 元素名含 `$1.00` | 用 `getByText("Verify with")` 或 `\$` 转义 `[实测]` |
| 目录很多"Free"模型 | 免费档受 hourly/daily 限额；Credits 页可切「Free models past the daily limit」策略（Stop at the free limit / 付费继续）；Pro($20/mo) 才完全免 ds-v4.1-flash/gpt-6-luna/jev | 看 Credits 页 Plan 区 `[文档+实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/expl_call.py | 最小调用封装：`EXPLABS_API_KEY` env→`~/.explabs_api_key` 回退、打印 usage/provider |
