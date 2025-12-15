from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright
import os
import time
import base64

app = FastAPI()

EXTENSION_PATH = os.path.abspath("./vidfast-extension")

# READ PROXY FROM ENVIRONMENT (Settings -> Environment Variables in Render)
# Format should be: http://user:pass@ip:port
PROXY_STRING = "http://kobxbjoj:y2x3x7ewuxj1@142.111.48.253:7030" 

def run_scraper_with_extension(video_url):
    print(f"🚀 Launching Browser for: {video_url}")
    print(f"🌍 Using Proxy: {PROXY_STRING if PROXY_STRING else 'None (Expect Block)'}")
    
    debug_screenshot = None
    
    with sync_playwright() as p:
        # CONFIGURE PROXY
        proxy_config = {"server": PROXY_STRING} if PROXY_STRING else None

        context = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome_user_data", 
            headless=False, 
            
            # --- NEW: PROXY SETTINGS ---
            proxy=proxy_config, 
            
            args=[
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--headless=new", 
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--autoplay-policy=no-user-gesture-required"
            ],
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        # Anti-Bot Script (Still needed even with proxy)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        try:
            print("Navigating...")
            # Increased timeout because proxies can be slow
            page.goto(video_url, timeout=90000, wait_until="domcontentloaded")
            
            # Wiggle & Click Logic
            print("Interacting with page...")
            time.sleep(5)
            page.mouse.click(960, 540) # Click center
            
            # Wait for extension
            print("⏳ Waiting 15s for extension...")
            time.sleep(15)
            
            # Take Screenshot
            screenshot_bytes = page.screenshot(full_page=False)
            debug_screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")
            
            result = "Finished."

        except Exception as e:
            print(f"❌ Error: {e}")
            result = str(e)
            
        context.close()
        return result, debug_screenshot

@app.get("/debug-view")
def debug_view(url: str):
    status, screenshot = run_scraper_with_extension(url)
    if screenshot:
        html_content = f"""
        <html><body>
            <h1>Debug View</h1>
            <p><b>Status:</b> {status}</p>
            <p><b>Proxy Used:</b> {PROXY_STRING}</p>
            <img src="data:image/png;base64,{screenshot}" style="max-width:100%; border: 2px solid red;" />
        </body></html>
        """
        return Response(content=html_content, media_type="text/html")
    return {"error": "Failed", "details": status}
