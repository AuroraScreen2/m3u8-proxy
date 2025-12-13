from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import random
import time

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"title": "Unknown", "url": "Unknown", "status": "Starting"}
    
    with sync_playwright() as p:
        # 1. SETUP: Use exact User Agent
        my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        
        # 2. LAUNCH: Add args to fake a real screen
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        )

        # 3. CONTEXT: Set Timezone & Locale (Servers usually show UTC, which is suspicious)
        context = browser.new_context(
            user_agent=my_user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York", 
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1"
            }
        )

        # 4. STEALTH: Delete WebDriver flag
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()
        
        # Listener
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
            page.goto("https://vidfast.pro/movie/533535", timeout=60000, wait_until="domcontentloaded")
            
            # 5. HUMAN SIMULATION LOOP
            # We wait 20 seconds, but we move the mouse every 1 second.
            debug_info["status"] = "Simulating human behavior..."
            
            for i in range(20):
                if len(results) >= 2:
                    break
                
                # A: Move Mouse Randomly
                x = random.randint(100, 1000)
                y = random.randint(100, 800)
                page.mouse.move(x, y)
                
                # B: Scroll a tiny bit
                page.mouse.wheel(0, 100)
                
                # C: Wait
                page.wait_for_timeout(1000)

            # Debugging capture
            if not results:
                debug_info["status"] = "Timed out waiting for data."
                debug_info["title"] = page.title()
                debug_info["url"] = page.url
                try:
                    # Capture text near the center of the screen
                    debug_info["content_snippet"] = page.inner_text("body")[:300]
                except:
                    debug_info["content_snippet"] = "Empty body"

        except Exception as e:
            debug_info["error"] = str(e)
            print(f"Error: {e}")
            
        browser.close()
        
    return results, debug_info

@app.get("/scrape")
def run_scraper():
    data, debug = scrape_logic()
    
    if data:
        return {"status": "success", "count": len(data), "data": data}
    
    return {
        "status": "failed", 
        "message": "No data found", 
        "debug": debug
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
