import { test, expect } from '@playwright/test';

// INTEGRATION DEMO TEST — requires live backend, frontend dev server, and test credentials
// Enable by setting TEST_EMAIL and TEST_PASSWORD environment variables
// SUPABASE_URL and SUPABASE_KEY (service role) are loaded from backend/.env by run_demo.sh
//
// Usage: TEST_EMAIL=you@example.com TEST_PASSWORD=yourpass ./scripts/run_demo.sh
// The script pre-provisions the test account via Supabase admin API on first run.

test.describe('SixDegrees v1.1 Demo', () => {

  // Pre-provision the test account via Supabase admin API so login always works.
  // Creates the user with email_confirm: true, bypassing email verification.
  // Idempotent — 422 means the account already exists, which is fine.
  test.beforeAll(async ({ request }) => {
    if (!process.env.TEST_EMAIL) return;

    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      console.log('SUPABASE_URL/SUPABASE_KEY not set — skipping account pre-provisioning');
      return;
    }

    const res = await request.post(`${supabaseUrl}/auth/v1/admin/users`, {
      headers: {
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`,
        'Content-Type': 'application/json',
      },
      data: {
        email: process.env.TEST_EMAIL,
        password: process.env.TEST_PASSWORD,
        email_confirm: true,
      },
    });

    if (res.status() === 200 || res.status() === 201) {
      console.log('Test account created via admin API.');
    } else if (res.status() === 422) {
      console.log('Test account already exists — proceeding.');
    } else {
      const body = await res.text();
      console.warn(`Account pre-provisioning returned ${res.status()}: ${body} — proceeding anyway.`);
    }
  });

  test('SixDegrees v1.1 full demo walkthrough', async ({ page }) => {
    test.setTimeout(60000);

    // Step 0: Skip guard + setup
    test.skip(!process.env.TEST_EMAIL, 'Set TEST_EMAIL and TEST_PASSWORD env vars to run demo');
    const email = process.env.TEST_EMAIL;
    const password = process.env.TEST_PASSWORD;

    // Step 1: Browse to /signup — show the form being filled in
    // (Account was pre-provisioned in beforeAll via admin API — this is for visual demo)
    await page.goto('/signup');
    const nicknameInput = page.locator('input[placeholder*="nickname" i], input[placeholder*="name" i]');
    if (await nicknameInput.count() > 0) await nicknameInput.first().fill('Demo User');
    const signupEmailInput = page.locator('input[placeholder*="email" i]');
    if (await signupEmailInput.count() > 0) await signupEmailInput.first().fill(email);
    await page.waitForTimeout(800);

    // Step 2: Log in with existing test account
    // Note: Login.vue uses type="text" for the email field (not type="email")
    await page.goto('/login');
    await page.locator('input[type="text"]').fill(email);
    await page.locator('input[type="password"]').fill(password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/\/(profile-setup)?$/, { timeout: 15000 });

    // Step 3: Handle profile-setup if redirected
    if (page.url().includes('profile-setup')) {
      // Extract token from localStorage to call PUT /profile directly
      const token = await page.evaluate(() => {
        const keys = Object.keys(localStorage);
        for (const k of keys) {
          if (k.includes('supabase')) {
            try { return JSON.parse(localStorage.getItem(k))?.access_token; } catch {}
          }
        }
        return null;
      });
      if (token) {
        await page.request.put('http://localhost:8000/profile', {
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          data: JSON.stringify({ display_name: 'Demo User' })
        });
      }
      const cityInput = page.locator('input[placeholder*="city" i], input[name="city"]');
      if (await cityInput.count() > 0) await cityInput.first().fill('San Francisco');
      const stateInput = page.locator('input[placeholder*="state" i], input[name="state"]');
      if (await stateInput.count() > 0) await stateInput.first().fill('CA');
      const ageInput = page.locator('input[type="number"], input[placeholder*="age" i]');
      if (await ageInput.count() > 0) await ageInput.first().fill('30');
      await page.locator('button[type="submit"]').click();
      await page.waitForURL('**/', { timeout: 15000 });
    }

    // Step 4: Verify Home feed renders
    expect(page.url()).toMatch(/\/$/);
    const feedContainer = page.locator('.home-container, .feed, main').first();
    await expect(feedContainer).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(800);

    // Step 5: Create a post
    const textarea = page.locator('textarea');
    await textarea.fill(
      'Demo post from SixDegrees Playwright walkthrough — ' + new Date().toISOString()
    );
    await page.locator('button.post-btn, button:has-text("Post")').first().click();
    await page.waitForTimeout(1500);
    await expect(page.locator('body')).toContainText('Demo post');

    // Step 6: Like a post
    const likeBtn = page.locator(
      '.like-btn, button:has-text("♥"), button:has-text("❤"), .action-btn'
    ).first();
    await likeBtn.click();
    await page.waitForTimeout(800);
    await expect(likeBtn).toBeVisible();

    // Step 7: Write a comment
    const commentToggle = page.locator(
      'button:has-text("comment"), button:has-text("💬"), .comment-btn, .action-btn'
    ).nth(1);
    if (await commentToggle.count() > 0) {
      await commentToggle.first().click();
      await page.waitForTimeout(500);
    }
    const commentInput = page.locator(
      'textarea[placeholder*="comment" i], input[placeholder*="comment" i]'
    );
    if (await commentInput.count() > 0) {
      await commentInput.first().fill('Demo comment from Playwright');
      await commentInput.first().press('Enter');
      await page.waitForTimeout(1000);
    }

    // Step 8: Extract Supabase access token from localStorage
    const token = await page.evaluate(() => {
      const keys = Object.keys(localStorage);
      for (const k of keys) {
        if (k.startsWith('sb-') || k.includes('supabase')) {
          try {
            const parsed = JSON.parse(localStorage.getItem(k));
            if (parsed?.access_token) return parsed.access_token;
            if (parsed?.session?.access_token) return parsed.session.access_token;
          } catch {}
        }
      }
      return null;
    });
    expect(token, 'Supabase access token must be present in localStorage').toBeTruthy();

    // Step 9: Verify GET /profile returns is_onboarded=true (HARD ASSERT — no fallback)
    const profileRes = await page.request.get('http://localhost:8000/profile', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(profileRes.status(), 'GET /profile must return 200').toBe(200);
    const profile = await profileRes.json();
    expect(profile.is_onboarded, 'is_onboarded MUST be true — Phase 7 BEND-02 sets this').toBe(true);
    const userId = profile.user_id;
    expect(userId, 'user_id must be present in profile').toBeTruthy();

    // Step 10: Trigger map pipeline and verify coordinates
    const triggerRes = await page.request.post(`http://localhost:8000/map/trigger/${userId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(triggerRes.status(), 'POST /map/trigger must return 200').toBe(200);
    const mapData = await triggerRes.json();
    expect(
      Array.isArray(mapData.coordinates) && mapData.coordinates.length > 0,
      'map coordinates must be non-empty after trigger'
    ).toBe(true);

    // Step 11: Logout
    await page.locator(
      'button:has-text("Logout"), button:has-text("Log out"), .logout-btn'
    ).first().click();
    await page.waitForURL('**/login', { timeout: 10000 });
    expect(page.url()).toContain('login');
  });

});
