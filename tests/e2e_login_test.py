"""E2E test for login screen."""

import sys
from playwright.sync_api import sync_playwright

ERRORS = []
PASSED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS: {name}")
    else:
        ERRORS.append(name)
        print(f"  FAIL: {name} {detail}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # ── 1. Login screen shows ──
        print("\n== 1. Login Screen ==")
        page.goto("http://localhost:3333")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/yt_e2e_login_01.png", full_page=True)

        check("Login screen visible",
              page.locator("#loginScreen").is_visible())
        check("App shell hidden",
              not page.locator("#appShell").is_visible())
        check("Email input exists",
              page.locator("#loginEmail").count() > 0)
        check("Password input exists",
              page.locator("#loginPassword").count() > 0)

        # ── 2. Wrong credentials ──
        print("\n== 2. Wrong Credentials ==")
        page.fill("#loginEmail", "wrong@test.com")
        page.fill("#loginPassword", "wrongpass")
        page.click("text=Inloggen")
        page.wait_for_timeout(500)

        check("Error message shown",
              page.locator("#loginError").text_content() != "")
        check("Still on login screen",
              page.locator("#loginScreen").is_visible())

        # ── 3. Correct credentials ──
        print("\n== 3. Correct Login ==")
        page.fill("#loginEmail", "admin@youtubefactory.nl")
        page.fill("#loginPassword", "factory2026!")
        page.click("text=Inloggen")
        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/yt_e2e_login_02_loggedin.png", full_page=True)

        check("Login screen hidden",
              not page.locator("#loginScreen").is_visible())
        check("App shell visible",
              page.locator("#appShell").is_visible())
        check("Mode buttons visible",
              page.locator("button.mode-btn").count() >= 4)

        # ── 4. Token persists on reload ──
        print("\n== 4. Token Persistence ==")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)

        check("Still logged in after reload",
              page.locator("#appShell").is_visible())
        check("Login screen still hidden",
              not page.locator("#loginScreen").is_visible())

        # ── 5. API calls work with token ──
        print("\n== 5. Authenticated API ==")
        token = page.evaluate("() => localStorage.getItem('yt_factory_token')")
        check("Token stored in localStorage", token is not None and len(token) > 20)

        resp = page.request.get("http://localhost:3333/api/voices", headers={
            "Authorization": f"Bearer {token}"
        })
        check("API /voices with token returns 200", resp.status == 200)

        resp_noauth = page.request.get("http://localhost:3333/api/voices")
        check("API /voices without token returns 401", resp_noauth.status == 401)

        # ── 6. Logout ──
        print("\n== 6. Logout ==")
        page.click("text=Uitloggen")
        page.wait_for_timeout(300)
        page.screenshot(path="/tmp/yt_e2e_login_03_logout.png", full_page=True)

        check("Login screen shows after logout",
              page.locator("#loginScreen").is_visible())
        check("App shell hidden after logout",
              not page.locator("#appShell").is_visible())

        token_after = page.evaluate("() => localStorage.getItem('yt_factory_token')")
        check("Token cleared from localStorage", token_after is None)

        browser.close()

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"RESULTS: {len(PASSED)} passed, {len(ERRORS)} failed")
    if ERRORS:
        print(f"\nFailed tests:")
        for e in ERRORS:
            print(f"  - {e}")
    print(f"{'='*50}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
