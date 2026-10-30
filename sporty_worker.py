import time
import random
import re
import json
import os
import logging
import requests
from datetime import date
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Centralized selectors for SportyBet Nigeria
SPORTY_CONFIG = {
    "BASE_URL": "https://www.sportybet.com/ng/",
    "BOOK_BET_BUTTON": "button:has-text('Book'), button:has-text('Book Bet'), .m-book-btn",
    "BOOKING_CODE_MODAL": ".m-dialog-content, .booking-code-modal, .m-pop-container",
    "BOOKING_CODE_TEXT": ".booking-code, .share-code, .code-text, span.strong"
}

CACHE_FILE = "booking_cache.json"

def get_cached_codes() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def update_cached_code(slip_key: str, code: str):
    data = get_cached_codes()
    data[slip_key] = {
        "code": code,
        "date": str(date.today())
    }
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to persist booking code: {e}")

def random_delay(min_sec=1.2, max_sec=2.5):
    time.sleep(random.uniform(min_sec, max_sec))

# =====================================================================
# HEADLESS PLAYWRIGHT BROWSER WORKER
# =====================================================================
def automate_sportybet_booking(selections: list, slip_key: str = "3_odds") -> str:
    """
    Automates booking real SportyBet Nigeria slips via Playwright.
    """
    if not selections:
        return "N/A"

    # Check cache first
    cached = get_cached_codes().get(slip_key)
    if cached and cached.get("date") == str(date.today()) and cached.get("code"):
        logging.info(f"Returning cached booking code for {slip_key}: {cached['code']}")
        return cached["code"]

    logging.info(f"Launching Headless Playwright Worker for SportyBet Nigeria [{slip_key}]...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1280,800"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-NG",
            timezone_id="Africa/Lagos"
        )
        page = context.new_page()

        # Stealth evasion
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
        """)

        booking_code = None

        try:
            logging.info("Navigating to SportyBet Nigeria...")
            page.goto(SPORTY_CONFIG["BASE_URL"], timeout=45000, wait_until="domcontentloaded")
            random_delay(2.0, 3.5)

            # Close promo popups if any
            try:
                dismiss_btn = page.locator("button:has-text('Accept'), button:has-text('Confirm'), .m-close, .es-dialog-close")
                if dismiss_btn.first.is_visible(timeout=3000):
                    dismiss_btn.first.click()
            except Exception:
                pass

            # Search and add every match
            for item in selections:
                home_team = item["home"]
                market_label = item.get("market", "")

                encoded_search = requests.utils.quote(home_team)
                page.goto(f"https://www.sportybet.com/ng/sport/football/search?keyword={encoded_search}", wait_until="domcontentloaded")
                random_delay(1.5, 2.5)

                match_locator = page.locator(".m-table-row, .m-match-item").first
                if not match_locator.is_visible(timeout=5000):
                    continue

                outcome_btn = None
                if "Over 1.5" in market_label:
                    outcome_btn = match_locator.locator("button:has-text('Over 1.5'), [data-market='over-1.5'], .m-outcome-item:has-text('Over 1.5')").first
                elif "1X" in market_label:
                    outcome_btn = match_locator.locator("button:has-text('1X'), .m-outcome-item:has-text('1X')").first
                elif "X2" in market_label:
                    outcome_btn = match_locator.locator("button:has-text('X2'), .m-outcome-item:has-text('X2')").first
                elif "DNB" in market_label:
                    outcome_btn = match_locator.locator("button:has-text('DNB'), .m-outcome-item:has-text('1')").first

                if outcome_btn and outcome_btn.is_visible(timeout=3000):
                    outcome_btn.click()
                    random_delay(0.8, 1.4)

            # Click Book Bet
            logging.info("Clicking Book Bet on SportyBet...")
            book_button = page.locator(SPORTY_CONFIG["BOOK_BET_BUTTON"]).first
            
            if book_button.is_visible(timeout=4000):
                book_button.click()
                random_delay(2.0, 3.5)

                modal = page.locator(SPORTY_CONFIG["BOOKING_CODE_MODAL"]).first
                if modal.is_visible(timeout=6000):
                    modal_text = modal.inner_text()
                    matches = re.findall(r"\b([A-Z0-9]{6,8})\b", modal_text)
                    if matches:
                        booking_code = matches[0]
                        logging.info(f"Booking Code Acquired: {booking_code}")

            if not booking_code:
                code_elem = page.locator(".share-code-content, .booking-code-num").first
                if code_elem.is_visible(timeout=2000):
                    booking_code = code_elem.inner_text().strip()

        except Exception as e:
            logging.error(f"Worker exception: {e}")
        finally:
            context.close()
            browser.close()

        if booking_code:
            update_cached_code(slip_key, booking_code)
            return booking_code

        fallback = get_cached_codes().get(slip_key, {}).get("code", "BC-READY")
        return fallback
