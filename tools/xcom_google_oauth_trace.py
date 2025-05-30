import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    filename="tools/xcom_google_oauth_trace.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

XCOM_URL = "https://x.com"
GOOGLE_EMAIL = "YOUR_TEST_EMAIL"
GOOGLE_PASSWORD = "YOUR_TEST_PASSWORD"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            logging.info("Navigating to x.com")
            await page.goto(XCOM_URL)
            await page.screenshot(path="tools/step1_xcom_home.png")
            logging.info("Page loaded: %s", page.url)

            # Click the login/sign-in button (update selector as needed)
            logging.info("Clicking login/sign-in button")
            await page.click('text=Sign in')
            await page.screenshot(path="tools/step2_signin_clicked.png")

            # Click the Google sign-in button (update selector as needed)
            logging.info("Clicking Google sign-in button")
            await page.click('button:has-text("Google")')
            await page.screenshot(path="tools/step3_google_clicked.png")

            # Switch to Google OAuth popup
            logging.info("Waiting for Google OAuth popup")
            popup = await context.wait_for_event("page")
            await popup.wait_for_load_state()
            logging.info("Google OAuth popup loaded: %s", popup.url)
            await popup.screenshot(path="tools/step4_google_oauth.png")

            # Enter email
            logging.info("Entering Google email")
            await popup.fill('input[type="email"]', GOOGLE_EMAIL)
            await popup.screenshot(path="tools/step5_email_entered.png")
            await popup.click('button:has-text("Next")')

            # Enter password
            await popup.wait_for_selector('input[type="password"]', timeout=10000)
            logging.info("Entering Google password")
            await popup.fill('input[type="password"]', GOOGLE_PASSWORD)
            await popup.screenshot(path="tools/step6_password_entered.png")
            await popup.click('button:has-text("Next")')

            # Wait for redirect back to x.com
            await popup.wait_for_close(timeout=20000)
            logging.info("Google OAuth popup closed, waiting for x.com UI update")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.screenshot(path="tools/step7_post_login.png")

            # Check for credential extraction/UI update (update selector as needed)
            if await page.query_selector('text=Profile') or await page.query_selector('img[alt="Profile"]'):
                logging.info("UI updated: Profile detected after login")
            else:
                logging.warning("UI did not update as expected after login")

        except Exception as e:
            logging.error("Error during automation: %s", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())