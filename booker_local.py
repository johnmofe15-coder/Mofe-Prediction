import os
import requests
from playwright.sync_api import sync_playwright

# Your credentials from jsonbin.io
JSONBIN_BIN_ID = "YOUR_BIN_ID_HERE"
JSONBIN_API_KEY = "YOUR_API_KEY_HERE"

def get_live_selections():
    """Fetches the latest match list from your active app."""
    # In practice, your app can expose a JSON endpoint, or you define the 4 target teams for today:
    return [
        {"home": "Real Madrid", "market": "Over 1.5"},
        {"home": "Bayern Munich", "market": "Over 1.5"},
        {"home": "Arsenal", "market": "1X"},
        {"home": "Paris Saint-Germain", "market": "Over 1.5"}
    ]

def auto_book_on_sportybet():
    selections = get_live_selections()
    print("Launching local browser to book SportyBet Nigeria ticket...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-NG",
            timezone_id="Africa/Lagos"
        )
        page = context.new_page()

        try:
            page.goto("https://www.sportybet.com/ng/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            for item in selections:
                team = item["home"]
                market = item["market"]
                print(f"Adding match: {team} -> {market}")
                page.goto(f"https://www.sportybet.com/ng/sport/football/search?keyword={team}", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                match_row = page.locator(".m-table-row, .m-match-item").first
                if match_row.is_visible():
                    if "Over 1.5" in market:
                        btn = match_row.locator("button:has-text('Over 1.5')").first
                    else:
                        btn = match_row.locator("button:has-text('1X')").first
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(1000)

            # Click Book Bet
            print("Booking ticket...")
            book_btn = page.locator("button:has-text('Book'), button:has-text('Book Bet'), .m-book-btn").first
            if book_btn.is_visible():
                book_btn.click()
                page.wait_for_timeout(3500)

                modal_text = page.locator(".m-dialog-content, .booking-code-modal").first.inner_text()
                import re
                code_match = re.findall(r"\b([A-Z0-9]{6,8})\b", modal_text)
                if code_match:
                    real_code = code_match[0]
                    print(f"SUCCESS! Real SportyBet Nigeria Code: {real_code}")

                    # Push code to JSONBin cloud database
                    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
                    payload = {
                        "board_master": real_code,
                        "stake_5": real_code,
                        "stake_10": real_code,
                        "stake_20": real_code,
                        "3_odds": real_code,
                        "5_odds": real_code,
                        "10_odds": real_code,
                        "20_odds": real_code
                    }
                    res = requests.put(f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}", json=payload, headers=headers)
                    if res.status_code == 200:
                        print("Synced to your Streamlit app successfully. Refresh your app to see the code live!")
        finally:
            browser.close()

if __name__ == "__main__":
    auto_book_on_sportybet()
