// 用法：scripts/tab_run.sh <task> scripts/get_title.js
// 新开页访问 example.com，回传标题与正文片段（验证整条链路的最小程序）
await page.goto("https://example.com", { waitUntil: "domcontentloaded" });
const text = (await page.locator("body").innerText({ timeout: 15000 })).slice(0, 200);
return { title: await page.title(), url: page.url(), text };
