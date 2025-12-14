from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import random

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"status": "Starting"}
    
    with sync_playwright() as p:
        # Use your exact User Agent
        my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling", # <--- NEW: Stops background timers from slowing down
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        )

        context = browser.new_context(
            user_agent=my_user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        
        # --- 1. THE VISIBILITY HACK ---
        # This forces the browser to report "I am visible!" 100% of the time.
        context.add_init_script("""
            Object.defineProperty(document, 'visibilityState', {
                get: () => 'visible'
            });
            Object.defineProperty(document, 'hidden', {
                get: () => false
            });
            // Also fake the "focus" events
            window.dispatchEvent(new Event('focus'));
            document.dispatchEvent(new Event('visibilitychange'));
        """)

        # --- 2. DELETE WEBDRIVER FLAG ---
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()
        
        def handle_response(response):
            if "/hezushon/ge/" in response.url:
                try:
                    data = response.json()
                    if data not in results:
                        results.append(data)
                except:
                    pass

        page.on("response", handle_response)
        
        try:
            print("Navigating...")
            page.goto("https://vidfast.pro/movie/155?autoplay=true", timeout=60000, wait_until="domcontentloaded")
            
            # --- 3. FORCE FOCUS ---
            # Tell the browser "Click here, look here!"
            page.bring_to_front()
            page.evaluate("window.focus()")
            page.click("body") # Click the page to ensure it's "active"
            
            # Wait loop
            for i in range(25):
                if len(results) >= 2:
                    break
                
                # Keep simulating activity so it doesn't think we went idle
                page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                page.evaluate("window.dispatchEvent(new Event('mousemove'));")
                
                page.wait_for_timeout(1000)

            # Debug Capture
            if not results:
                debug_info["status"] = "Timed out"
                debug_info["final_url"] = page.url
                try:
                    # Capture text to see if "FETCHING" is still there
                    debug_info["page_text"] = page.inner_text("body")[:300]
                except:
                    pass

        except Exception as e:
            debug_info["error"] = str(e)
            
        browser.close()
    return results, debug_info

@app.get("/scrape")
def run_scraper():
    data, debug = scrape_logic()
    if data:
        return {"status": "success", "count": len(data), "data": data}
    return {"status": "failed", "debug": debug}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
