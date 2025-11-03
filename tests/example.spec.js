const { test, expect } = require('@playwright/test');

test.describe('Naver Blog Playwright Test', () => {
  test.setTimeout(60000); // 60초 타임아웃 설정

  test('should open Naver homepage and verify title', async ({ page }) => {
    // Navigate to Naver
    await page.goto('https://www.naver.com', { waitUntil: 'domcontentloaded' });
    
    // Wait for page title
    await expect(page).toHaveTitle(/NAVER/i, { timeout: 10000 });
    
    // Verify page loaded
    await expect(page.locator('body')).toBeVisible();
  });

  test('should search for keyword on Naver', async ({ page }) => {
    // Navigate to Naver
    await page.goto('https://www.naver.com', { waitUntil: 'domcontentloaded' });
    
    // Wait for search box
    const searchBox = page.locator('#query');
    await searchBox.waitFor({ state: 'visible', timeout: 10000 });
    
    // Type search query
    await searchBox.fill('Playwright');
    
    // Press Enter to search instead of clicking button
    await searchBox.press('Enter');
    
    // Wait for navigation
    await page.waitForURL(/search.naver.com/, { timeout: 15000 });
    
    // Verify we're on the search results page
    await expect(page).toHaveURL(/search.naver.com/);
  });

  test('should navigate to Naver Blog and verify elements', async ({ page }) => {
    // Navigate to Naver Blog
    await page.goto('https://blog.naver.com', { waitUntil: 'domcontentloaded' });
    
    // Wait for page to load
    await expect(page).toHaveURL(/blog.naver.com/, { timeout: 15000 });
    
    // Check if main content area is visible
    const mainContent = page.locator('body');
    await expect(mainContent).toBeVisible({ timeout: 10000 });
  });

  test('should verify Playwright is working correctly', async ({ page }) => {
    // 간단한 테스트 - Playwright 공식 사이트로 동작 확인
    await page.goto('https://playwright.dev', { waitUntil: 'domcontentloaded' });
    
    // 페이지 제목 확인
    await expect(page).toHaveTitle(/Playwright/i, { timeout: 10000 });
    
    // 페이지가 로드되었는지 확인
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
    
    // 검색 기능 확인 (Playwright 사이트의 검색 버튼)
    const searchButton = page.locator('button[aria-label="Search"]').or(page.locator('button:has-text("Search")')).first();
    if (await searchButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchButton.click();
      await page.waitForTimeout(1000);
    }
  });
});

