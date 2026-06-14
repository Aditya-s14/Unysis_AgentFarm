import { chromium } from '@playwright/test';
import fs from 'fs';

const BASE = 'http://localhost:3002';
const OUT  = 'C:/Temp/af_shots/';
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx     = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page    = await ctx.newPage();

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(e.message));

async function shot(name) {
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: false });
  console.log('[shot] ' + name);
}

async function waitReady() {
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
}

// 1. Login page
console.log('\n=== 1. LOGIN PAGE ===');
await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
await waitReady();
const loginTitle = await page.title();
const hasOtpInput  = await page.locator('input[type="tel"]').count();
const hasDemoCards = await page.locator('button.glass-card').count();
console.log('title: ' + loginTitle);
console.log('OTP inputs: ' + hasOtpInput + ', demo cards: ' + hasDemoCards);
await shot('01_login');

// 2. FPO login
console.log('\n=== 2. FPO LOGIN ===');
if (hasDemoCards > 0) {
  const priyaBtn = page.locator('button', { hasText: 'Priya Sharma' });
  await priyaBtn.click();
  await page.waitForURL(/dashboard/, { timeout: 8000 }).catch(e => console.log('nav warn: ' + e.message));
} else if (hasOtpInput > 0) {
  await page.fill('input[type="tel"]', '+919800000001');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(2000);
  const bodyText = await page.locator('body').textContent();
  const otpMatch = bodyText.match(/\b(\d{6})\b/);
  console.log('found 6-digit in page: ' + (otpMatch ? otpMatch[1] : 'none'));
  const codeInput = await page.locator('input[placeholder*="code"], input[type="text"]').first();
  await codeInput.fill(otpMatch ? otpMatch[1] : '123456');
  await page.locator('button[type="submit"]').last().click();
  await page.waitForURL(/dashboard/, { timeout: 8000 }).catch(e => console.log('nav warn: ' + e.message));
} else {
  console.log('WARN: no login method found');
}
console.log('URL after login: ' + page.url());
await shot('02_after_login');

// 3. Dashboard
console.log('\n=== 3. DASHBOARD ===');
await page.goto(BASE + '/dashboard', { waitUntil: 'domcontentloaded' });
await waitReady();
const tabs = await page.locator('button').filter({ hasText: /^(OVERVIEW|FARMER|MANDI|TRANSPORT)$/ }).count();
console.log('Dashboard URL: ' + page.url() + ', tabs: ' + tabs);
await shot('03_dashboard');

// 4. Farmer tab
console.log('\n=== 4. FARMER TAB ===');
const farmerTab = page.locator('button').filter({ hasText: /^FARMER$/ }).first();
if (await farmerTab.count() > 0) {
  await farmerTab.click();
  await page.waitForTimeout(1200);
  const farmRows = await page.locator('text=kg at risk').count();
  console.log('farm rows: ' + farmRows);
  await shot('04_farmer_tab');
} else { console.log('WARN: no FARMER tab'); }

// 5. Mandi tab (crash check)
console.log('\n=== 5. MANDI TAB ===');
errors.length = 0;
const mandiTab = page.locator('button').filter({ hasText: /^MANDI$/ }).first();
if (await mandiTab.count() > 0) {
  await mandiTab.click();
  await page.waitForTimeout(1200);
  const errorOverlay = await page.locator('text=ReferenceError').count();
  console.log('error overlay: ' + errorOverlay + ', console errors: ' + errors.length);
  errors.forEach(e => console.log('  ' + e.slice(0, 100)));
  await shot('05_mandi_tab');
} else { console.log('WARN: no MANDI tab'); }

// 6. Transport tab
console.log('\n=== 6. TRANSPORT TAB ===');
const transTab = page.locator('button').filter({ hasText: /^TRANSPORT$/ }).first();
if (await transTab.count() > 0) {
  await transTab.click();
  await page.waitForTimeout(1200);
  const truckMentions = await page.locator('text=TR-').count();
  console.log('TR- mentions: ' + truckMentions);
  await shot('06_transport_tab');
} else { console.log('WARN: no TRANSPORT tab'); }

// 7. Farmer page (Ravi Kumar)
console.log('\n=== 7. FARMER PAGE ===');
const signOut1 = page.locator('button').filter({ hasText: /sign out/i }).first();
if (await signOut1.count() > 0) {
  await signOut1.click();
  await page.waitForURL(/login/, { timeout: 5000 }).catch(() => {});
}
await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
await waitReady();
const raviBtn = page.locator('button', { hasText: 'Ravi Kumar' });
if (await raviBtn.count() > 0) {
  await raviBtn.click();
  await page.waitForURL(/farmer/, { timeout: 8000 }).catch(e => console.log('nav warn: ' + e.message));
  await waitReady();
  const cropToggle = await page.locator('text=/CROP READY|NOT READY/').count();
  const truckETA   = await page.locator('text=/Truck ETA|No truck assigned/').count();
  const weather    = await page.locator('text=/7-Day Forecast/').count();
  console.log('crop: ' + cropToggle + ', eta: ' + truckETA + ', weather: ' + weather + ', url: ' + page.url());
  await shot('07_farmer_page');
} else { console.log('WARN: Ravi Kumar not found'); }

// 8. Mandi page (Shyam Iyer)
console.log('\n=== 8. MANDI PAGE ===');
errors.length = 0;
const signOut2 = page.locator('button').filter({ hasText: /sign out/i }).first();
if (await signOut2.count() > 0) {
  await signOut2.click();
  await page.waitForURL(/login/, { timeout: 5000 }).catch(() => {});
}
await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
await waitReady();
const shyamBtn = page.locator('button', { hasText: 'Shyam Iyer' });
if (await shyamBtn.count() > 0) {
  await shyamBtn.click();
  await page.waitForURL(/mandi/, { timeout: 8000 }).catch(e => console.log('nav warn: ' + e.message));
  await waitReady();
  await page.waitForTimeout(2000);
  const crash  = await page.locator('text=ReferenceError').count();
  const supply = await page.locator('text=/Supply Fulfilment|Incoming Trucks|Mandi Dashboard|Confirm/').count();
  console.log('crash: ' + crash + ', supply panels: ' + supply + ', url: ' + page.url());
  errors.forEach(e => console.log('  ERR: ' + e.slice(0, 120)));
  await shot('08_mandi_page');
} else { console.log('WARN: Shyam Iyer not found'); }

// 9. Summary
console.log('\n=== 9. ERROR SUMMARY ===');
console.log('Total errors: ' + errors.length);
errors.forEach(e => console.log('  ' + e.slice(0, 120)));

await browser.close();
console.log('\n=== DONE ===');
