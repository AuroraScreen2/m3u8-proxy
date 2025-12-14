from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import os
import time

app = FastAPI()

# Point to your extension folder
EXTENSION_PATH = os.path.abspath("./vidfast-extension")

def run_scraper_with_extension(video_url):
    print(f"🚀 Launching Browser with Extension for: {video_url}")
    
    with sync_playwright() as p:
        # We must use persistent_context to load extensions
        # We assume user_data_dir is inside /tmp to avoid permission errors on Render
        context = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome_user_data", 
            headless=True, # Note: Some extensions struggle in Headless, but we try 'new' mode via args
            args=[
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--headless=new", # Modern Headless mode (supports extensions better)
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ],
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()
        
        try:
            # 1. Go to the movie page
            page.goto(video_url, timeout=60000, wait_until="domcontentloaded")
            
            # 2. WAIT for the extension to work
            # The extension will detect the m3u8 and auto-send it to your Cloudflare Worker.
            # We just need to keep the browser open long enough for that to happen.
            print("⏳ Waiting 15s for extension to capture stream...")
            
            # Optional: Wiggle mouse to trigger the video player if needed
            for i in range(5):
                page.mouse.move(100 + i*10, 100 + i*10)
                time.sleep(1)
            
            # Wait a bit more to ensure upload finishes
            time.sleep(5) 
            
            result = "Scraping finished (Check Cloudflare Logs)"

        except Exception as e:
            print(f"❌ Error: {e}")
            result = str(e)
            
        context.close()
        return result

@app.get("/trigger-scrape")
def trigger_scrape(url: str):
    """
    Call this API to force the server to visit a link.
    Usage: GET /trigger-scrape?url=https://vidfast.pro/movie/533535
    """
    status = run_scraper_with_extension(url)
    return {"status": "completed", "message": status}
