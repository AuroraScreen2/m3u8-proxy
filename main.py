from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright
import os
import time
import base64

app = FastAPI()

EXTENSION_PATH = os.path.abspath("./vidfast-extension")

def run_scraper_with_extension(video_url):
    print(f"🚀 Launching Browser for: {video_url}")
    debug_screenshot = None
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome_user_data", 
            headless=False, # Required for extensions
            args=[
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--headless=new", 
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--autoplay-policy=no-user-gesture-required" # <--- NEW: Force Autoplay
            ],
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        # 1. INJECT ANTI-BOT SCRIPT (To pass "FETCHING" screen)
        # This deletes the 'webdriver' flag and fakes a GPU
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)
        
        try:
            print("Navigating...")
            page.goto(video_url, timeout=60000, wait_until="domcontentloaded")
            
            # 2. WAIT & WIGGLE (Bypass "Fetching")
            print("fighting 'Fetching' screen...")
            for i in range(5):
                page.mouse.move(200 + i*50, 200 + i*50)
                page.mouse.down()
                page.mouse.up()
                time.sleep(1)

            # 3. AGGRESSIVE CLICKER (Force Video Play)
            # VidFast often puts the video in an iframe. We click the center of the screen.
            print("Attempting to click Play...")
            
            # Click dead center of screen
            page.mouse.click(960, 540)
            time.sleep(1)
            
            # Try finding iframes and clicking them
            for frame in page.frames:
                try:
                    # Click inside every iframe found
                    box = frame.frame_element().bounding_box()
                    if box:
                        x = box['x'] + box['width'] / 2
                        y = box['y'] + box['height'] / 2
                        page.mouse.click(x, y)
                        print(f"Clicked iframe at {x},{y}")
                except:
                    pass

            # 4. WAIT FOR SNIFFER
            print("⏳ Video should be playing. Waiting 15s for extension...")
            time.sleep(15)
            
            # 5. TAKE DEBUG SCREENSHOT
            # This is crucial. If it fails, we need to see what the bot saw.
            screenshot_bytes = page.screenshot(full_page=False)
            debug_screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")
            
            result = "Finished. Check Screenshot to verify video played."

        except Exception as e:
            print(f"❌ Error: {e}")
            result = str(e)
            
        context.close()
        return result, debug_screenshot

@app.get("/trigger-scrape")
def trigger_scrape(url: str):
    status, screenshot = run_scraper_with_extension(url)
    
    # We return the screenshot in the JSON so you can debug
    return {
        "status": "completed", 
        "message": status,
        "screenshot_base64": screenshot[:100] + "..." if screenshot else "None" # Truncated for log
    }

# NEW: Endpoint to view the screenshot directly
@app.get("/debug-view")
def debug_view(url: str):
    status, screenshot = run_scraper_with_extension(url)
    if screenshot:
        html_content = f"""
        <html>
            <body>
                <h1>Debug View</h1>
                <p><b>Status:</b> {status}</p>
                <img src="data:image/png;base64,{screenshot}" style="max-width:100%; border: 2px solid red;" />
            </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")
    return {"error": "Failed to capture screenshot", "details": status}
