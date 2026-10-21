// 通过 API Explorer 调试台批量添加 DNS 记录（绕过云解析控制台「添加记录」UI bug）
// 在 tabbit Node 桥上下文中执行：`page` 为已登录阿里云的 Playwright Page 对象。
//
// 用法：改 RECS 后交给 tabbit 执行即可。每条记录：
//   1) 带 ?params= 的 URL 预填表单（避免 antd 输入框不吃程序化赋值）
//   2) 点「发起调用」→ 若有确认弹层点「我已确认参数，继续发起调用」（可勾不再提示）
//   3) 回收 POST /api/auth/product/openAPIRequest 的响应（RecordId=成功，DomainRecordDuplicate=已存在）

const resps = [];
page.on('response', async rs => {
  if (rs.request().method() === 'POST' && /openAPIRequest/.test(rs.url())) {
    try { const j = JSON.parse(await rs.text()); resps.push(j?.data?.result || j); } catch (e) {}
  }
});

const BASE = 'https://api.aliyun.com/api/Alidns/2015-01-09/AddDomainRecord?RegionId=cn-hangzhou&params=';
const DOMAIN = 'sigeer.xyz';   // 改成你的 zone 名
const SUB = 'ai';              // 邮箱子域 RR（主域直挂则换成 @ 或对应 RR）

const RECS = [
  // 所有权验证 CNAME（token 从邮箱控制台「更换域名 → 现在验证」页复制）
  {rr: 'aliMail<TOKEN>.' + SUB, t: 'CNAME', v: 'qiye.aliyun.com'},
  {rr: 'aliMail<TOKEN>',        t: 'CNAME', v: 'qiye.aliyun.com'},
  // MX ×3 + SPF
  {rr: SUB, t: 'MX',  v: 'mx1.qiye.aliyun.com', pri: 5},
  {rr: SUB, t: 'MX',  v: 'mx2.qiye.aliyun.com', pri: 10},
  {rr: SUB, t: 'MX',  v: 'mx3.qiye.aliyun.com', pri: 15},
  {rr: SUB, t: 'TXT', v: 'v=spf1 include:spf.qiye.aliyun.com -all'},
];

const results = [];
for (const rec of RECS) {
  resps.length = 0;
  const params = {DomainName: DOMAIN, RR: rec.rr, Type: rec.t, Value: rec.v, TTL: 600, Line: 'default'};
  if (rec.pri !== undefined) params.Priority = rec.pri;
  await page.goto(BASE + encodeURIComponent(JSON.stringify(params)), {waitUntil: 'domcontentloaded', timeout: 60000});
  await page.waitForTimeout(5000);
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find(b => (b.innerText||'').trim() === '发起调用' && b.offsetHeight > 0);
    if (btn) btn.click();
  });
  for (let i = 0; i < 25 && resps.length === 0; i++) {
    await page.waitForTimeout(1000);
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find(b => /继续发起调用/.test(b.innerText||'') && b.offsetHeight > 0);
      if (btn) btn.click();
    });
  }
  results.push({
    rec: rec.rr + '/' + rec.t,
    resp: resps[0] ? {RecordId: resps[0].RecordId, Code: resps[0].Code, Message: resps[0].Message} : 'NO-RESPONSE',
  });
}
return results;
