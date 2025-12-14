from playwright.sync_api import sync_playwright
import time
import os

# Path to your extension folder
EXTENSION_PATH = os.path.abspath("./vidfast-extension")

def run_bot(target_url):
    with sync_playwright() as p:
        # Launch Chrome with the Extension loaded
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./user_data", # Keeps cookies/settings
            headless=False, # Extensions often need "Headless=False" to work properly
            args=[
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--no-sandbox"
            ]
        )

        page = browser.new_page()
        
        print(f"🤖 Bot visiting: {target_url}")
        page.goto(target_url, timeout=60000)

        # Wait for the video to load (so the extension can sniff it)
        try:
            # Click play if needed to trigger the network request
            page.click("body", timeout=5000) 
        except:
            pass

        # Give the extension 10 seconds to find the link and send it to Cloudflare
        print("⏳ Waiting for extension to sniff...")
        time.sleep(10)

        print("✅ Done. Extension should have sent the data.")
        browser.close()

# List of movies you want to scrape automatically
movies_to_scrape = [
    "https://vidfast.pro/movie/533535",
    "https://vidfast.pro/movie/123456",
    "https://vidfast.pro/movie/987654"
]

for movie in movies_to_scrape:
    run_bot(movie)
