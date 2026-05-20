/**
 * E2E：镜像构建 · 上传 JAR 流程（需在 90s 内于打开的浏览器中完成登录）
 * 用法: node scripts/e2e-jar-step-build.mjs
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.cwd().includes('e2e-pkg')
  ? path.resolve(process.cwd(), '../..')
  : path.resolve(__dirname, '..');
const JAR = path.join(ROOT, 'test-artifacts', 'fake-demo.jar');
const BASE = process.env.APP2DOCKER_BASE || 'https://app2docker.jajachina.com';
const PROFILE = path.join(ROOT, '.pw-e2e-profile');

async function waitForLoggedIn(page, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const url = page.url();
    if (url.includes('/app/') && !url.includes('/login')) return true;
    if (url.includes('/login')) {
      await page.waitForTimeout(1500);
      continue;
    }
    await page.waitForTimeout(800);
  }
  return false;
}

async function main() {
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = context.pages()[0] || (await context.newPage());

  console.log('→ 打开', `${BASE}/app/step-build`);
  await page.goto(`${BASE}/app/step-build`, { waitUntil: 'domcontentloaded', timeout: 90000 });

  if (page.url().includes('/login')) {
    console.log('⚠️ 请在 Playwright 窗口登录（120 秒内）…');
    await page.waitForURL(/\/app\//, { timeout: 120000 });
    await page.goto(`${BASE}/app/step-build`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  }

  await page.waitForSelector('text=步骤 1：选择数据源', { timeout: 60000 });
  console.log('当前 URL:', page.url());

  // 步骤 1：上传文件
  await page.getByRole('button', { name: '上传文件' }).click({ timeout: 30000 });
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(JAR);
  console.log('✓ 已选择', JAR);

  await page.getByRole('button', { name: '下一步' }).first().click();

  // 步骤 2：Java + 模板
  await page.getByRole('button', { name: /Java 应用/ }).click();
  await page.waitForTimeout(500);
  // 文件上传模式默认走模板库
  const tplSearch = page.getByPlaceholder('搜索模板...');
  if (await tplSearch.isVisible().catch(() => false)) {
    await tplSearch.click();
    await page.waitForTimeout(800);
    const firstTpl = page.locator('.dropdown-item').first();
    if (await firstTpl.isVisible().catch(() => false)) {
      await firstTpl.click();
    }
  }
  await page.getByRole('button', { name: '下一步' }).click();

  // 步骤 3、4：默认下一步
  await page.getByRole('button', { name: '下一步' }).click();
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: '下一步' }).click();

  // 步骤 5：开始构建
  await page.waitForSelector('text=步骤 5：开始构建', { timeout: 15000 });
  const summary = page.locator('.build-summary-card, .card').first();
  if (await summary.isVisible().catch(() => false)) {
    console.log('✓ 最后一步摘要区域已渲染');
  }
  const uploadResp = page.waitForResponse(
    (r) => r.url().includes('/api/upload') && r.request().method() === 'POST',
    { timeout: 120000 }
  );
  await page.getByRole('button', { name: /开始构建/ }).click();

  let uploadStatus = '（未触发上传）';
  let uploadBody = '';
  try {
    const resp = await uploadResp;
    uploadStatus = String(resp.status());
    try {
      uploadBody = JSON.stringify(await resp.json());
    } catch {
      uploadBody = (await resp.text()).slice(0, 400);
    }
  } catch (e) {
    uploadStatus = `超时或失败: ${e.message}`;
  }
  console.log('上传 API:', uploadStatus, uploadBody.slice(0, 300));

  await page.waitForTimeout(2500);
  console.log('提交后 URL:', page.url());

  const toast = page.locator('text=构建任务已创建');
  if (await toast.isVisible().catch(() => false)) {
    console.log('✓ 提交成功 Toast');
  } else {
    const err = page.locator('text=构建失败, text=请先选择团队, text=Token');
    if (await err.first().isVisible().catch(() => false)) {
      console.log('✗ 错误提示:', await err.first().textContent());
    } else {
      console.log('? 未检测到 Toast，请到任务管理确认');
    }
  }

  await page.screenshot({ path: path.join(ROOT, 'test-artifacts', 'e2e-step5-result.png'), fullPage: true });
  console.log('截图已保存: test-artifacts/e2e-step5-result.png');
  await context.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
