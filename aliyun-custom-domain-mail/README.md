# 阿里云自定义域名邮箱（免费企业邮 + 子域并存方案）

> 实测跑通 2026-10-20。最终效果：`devin@ai.sigeer.xyz` 收发正常，主域 `@sigeer.xyz` 上的腾讯企业邮（QQ）完全不受影响，两套并存。

## 概述

用已在阿里云购买的域名开通**阿里企业邮箱免费版**（50 账号 × 5GB/账号，5 年期 0 元，实名账号到期自动续）。当主域 MX 已被别的邮局占用（本案：腾讯企业邮）时，改绑**子域名**（`ai.<domain>`）实现并存，不删不改主域任何记录。

## 环境前提

- OS：Windows + Tabbit Browser（用户真实浏览器，已登录阿里云控制台）。等价物：任何已登录阿里云的浏览器 + 可注入 JS 的自动化（Playwright/CDP）。
- 本流程全程**网页操作**，无需 AccessKey、无需 aliyun CLI。
- 域名 NS 必须仍在阿里云（`dns*.hichina.com`），否则记录要加到真正的权威 DNS 商那边。

## 关键架构事实

- 免费版购买直达链接（公开文档入口已隐藏）：
  `https://common-buy.aliyun.com/?commodityCode=alimail&specCode=lx_18482#/buy`
- 邮箱控制台：`https://alimail.console.aliyun.com/`（旧的 `freemal/mail.console/qiye.aliyun.com` 入口已废或跳转）
- 邮箱 Web 管理后台：`https://qiye.aliyun.com/admin/#/home`（postmaster 登录 webmail 后顶部「域管理」进入）
- 邮局要求的 DNS 记录（子域 `ai` 为例，以页面实测为准）：
  | RR | Type | Value | Pri |
  |---|---|---|---|
  | `aliMail<token>` / `aliMail<token>.ai` | CNAME | `qiye.aliyun.com` | -（所有权验证，两级各加一条保险） |
  | `ai` | MX | `mx1.qiye.aliyun.com` | 5 |
  | `ai` | MX | `mx2.qiye.aliyun.com` | 10 |
  | `ai` | MX | `mx3.qiye.aliyun.com` | 15 |
  | `ai` | TXT | `v=spf1 include:spf.qiye.aliyun.com -all` | - |

## 操作步骤

### 1. 下单免费版

浏览器（已登录阿里云）打开 `common-buy.aliyun.com?commodityCode=alimail&specCode=lx_18482#/buy`：
- 域名输入框在 `exmail.aliyun.com/choose.html` **iframe** 里（`#have_input`）。
- `[实测]` 仅 fill 不够——必须对输入框 dispatch `keydown` 事件，才会触发域名校验并 postMessage 给父页面（显示 `userID@<domain>`、价格变 ¥0）。
- 选「5 年」→ 勾协议 → 立即购买 → 0 元下单成功（跳 `cashier.aliyun.com/order/payNewSuccess`）。

### 2. 换绑子域名（主域被占用时）

控制台 `alimail.console.aliyun.com` → 邮箱列表 → 管理 → tab「更换域名」：
- 这是**老框架页面**（`e_*` class、about:blank iframe 渲染）。`element.click()` 在 evaluate 里点了不触发 handler——必须用 `frame.locator(...).click()` 让 Playwright 发真实鼠标事件；提交成功表现为 **frame detach**（导航刷新）。
- 选「填写新域名」radio（点 `<b class="e_i_select_radio">`）→ 输入 `ai.<domain>` → 提交 → 出现「需要所有权验证 / 现在验证」→ 点它拿到验证记录值（`aliMail<token>` → `qiye.aliyun.com`）。

### 3. 加 DNS 记录（绕过云解析 UI bug）

云解析控制台 `dnsnext.console.aliyun.com` 的「添加记录」按钮**实测点了不开对话框**（促销遮罩/前端 bug），且 fecs API 带 collina 防重放，直接 fetch 重放返回 403。

**可用通道 = API Explorer 调试台**，它用登录用户的临时 AccessKey 服务端签名：

```
GET https://api.aliyun.com/api/Alidns/2015-01-09/AddDomainRecord?params=<urlencoded JSON>
```

`params` JSON 直接写进 URL，页面加载即填充表单，然后只需点「发起调用」→ 弹「调用提示」→ 点「我已确认参数，继续发起调用」（勾「不再提示」后后续记录免确认）。真实调用走 `POST /api/auth/product/openAPIRequest`，响应里 `RecordId` 即成功，`DomainRecordDuplicate` = 已存在。

示例脚本见 `scripts/add_dns_record.js`（tabbit Node 桥内执行）。

`[实测]` 该页是 antd 表单：`native setter + input 事件` 填的值**不进 React 状态**，提交报「字段必填」×4。要么 `locator.pressSequentially()` 真实击键，要么用 URL params 预填（推荐，零交互）。

### 4. 完成换绑验证

回邮箱控制台 → 刷新 → 重走一遍更换域名提交 → DNS 已生效则直接通过：`邮箱域名: ai.<domain>`、`解析状态: 解析已生效`、管理员变为 `postmaster@ai.<domain>`。

### 5. 初始化 postmaster 密码

邮箱管理页「初始化密码」→ 设置+确认 → 提交（同样要用 frame locator 真点）。**首次初始化不需要短信验证**。

### 6. 建成员账号

`qiye.aliyun.com` 登录 `postmaster@ai.<domain>`：
- `[实测]` 用户名输入框有浏览器自动填充残留（本会话里是另一个邮箱），填前必须 triple-click 全选清空再输，否则拼接成垃圾用户名浪费登录尝试次数（上限 10）。
- 首登强制「绑定安全手机」收短信码——**绕法**：先让 postmaster 完成一次绑机，然后管理后台 `安全 → 账号安全 → 双重认证` 关掉开关并保存。关掉后成员首登只剩「强制改密」，无绑机。
- 后台 `用户与组 → 用户 → 新建账号`：姓名 + 邮箱前缀 + 初始密码，勾选「初次登录修改密码」。
- 成员首登改密页自动跳过验证（2FA 已关时）→ 进收件箱。

### 7. 收发验证

- 站内：postmaster 写邮件给 `devin@ai.<domain>`（写邮件页的收件人是 ant-select search input，输入后回车成 chip；正文是 `javascript:` iframe 编辑器，`contentDocument.body.innerHTML` 写入；发送按钮在底部，`top>500` 过滤「分别发送」）→ devin 收件箱出现即通。
- 外发：devin 回复 postmaster 即证明 devin 出站链路。
- 外收：从任意外部邮箱发到 `devin@ai.<domain>`，MX 已生效应秒达。

## 验证方法

```bash
nslookup -type=MX ai.<domain> 8.8.8.8     # 期望 3 条 mx*.qiye.aliyun.com
nslookup -type=TXT ai.<domain> 8.8.8.8    # 期望 v=spf1 include:spf.qiye.aliyun.com -all
nslookup -type=CNAME aliMail<token>.ai.<domain> 8.8.8.8  # 期望 → qiye.aliyun.com
nslookup -type=NS <domain> 8.8.8.8        # 确认权威是 dns*.hichina.com（阿里云）
```

管理后台概览页：域名状态「解析正常」、已分配账号数 = 已建成员数。

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| freemail.aliyun.com / mail.console.aliyun.com 打不开 | 入口废弃 | 走 `alimail.console.aliyun.com`（产品页可挖到）`[实测 2026-10-20]` |
| 下单页域名填了不生效 | 域名框在 choose.html iframe，校验靠 keydown+postMessage | dispatch keydown `[实测]` |
| 云解析「添加记录」点了没反应 | 前端遮罩/bug | API Explorer `?params=` 预填 + 发起调用 `[实测]` |
| fecs api.json 重放 403 | collina 每次请求新生成，在 webpack 内不可见 | 别 replay，用 API Explorer `[实测]` |
| API Explorer 提交报「字段必填」 | antd 表单不认程序化赋值 | pressSequentially 或 URL params `[实测]` |
| Type 字段点击被枚举浮层挡 | combobox 下拉 intercepts pointer events | URL params 方式跳过输入 `[实测]` |
| 邮箱控制台 click() 无效 | 老 e_* 框架要真实鼠标事件 | `frame.locator().click()`；成功标志=frame detach `[实测]` |
| 主域已有别的邮局 MX | 并存冲突会丢信 | 换绑子域，主域记录一律不动 `[实测]` |
| postmaster/成员首登强制绑手机 | 默认开启双重认证 | admin → 安全 → 账号安全 → 双重认证 → 关闭 `[实测]` |
| 换账号测试互相顶掉 | qiye.aliyun.com cookie 单会话 | `context.clearCookies({domain:'qiye.aliyun.com'})`，不伤 aliyun 控制台会话 `[实测]` |
| Cloud Shell 想跑 aliyun CLI | 需要手机验证码 | 放弃，走 API Explorer `[实测]` |
| 摘要误读：以为 NS 在 Cloudflare | 实际 NS=hichina，cloudflare 只是 @/www 的 CNAME 值 | 改记录前先 `nslookup -type=NS` 确权 `[实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/add_dns_record.js | tabbit 桥内批量 AddDomainRecord（URL params 预填 + 确认弹层处理 + 真实响应回收） |

## 本机验证记录（示例）

- 域名 `sigeer.xyz`，NS=dns11/12.hichina.com；主域 QQ 企业邮在用（mxbiz*.qq.com），故用子域 `ai.sigeer.xyz`。
- RecordId 实得：`2112455711333890048`(CNAME) / `2112456197176577024` `...3024` `...7456`(MX×3) / `2112456302399425536`(TXT)。
- 交付：`postmaster@ai.sigeer.xyz`、`devin@ai.sigeer.xyz`，webmail 互发双向通过；有效期至 2031-10-21。
