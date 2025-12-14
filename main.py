from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import random
import time

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"status": "Starting"}
    
    with sync_playwright() as p:
        # --- 1. USE LINUX USER AGENT (Matches Render's OS) ---
        # "X11; Linux x86_64" tells the truth about the server OS
        linux_user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = browser.new_context(
            user_agent=linux_user_agent, # <--- Updated to Linux
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                # --- 2. UPDATE HEADERS TO LINUX ---
                "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"', # <--- Vital: Matches the OS
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1"
            }
        )

        # Stealth: Remove Robot Flag
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
            # Use the autoplay url you found (it might help trigger the load)
            page.goto("https://vidfast.pro/movie/155?autoplay=true", timeout=60000, wait_until="domcontentloaded")
            
            # Wait loop
            debug_info["status"] = "Waiting on page..."
            for i in range(25):
                if len(results) >= 2:
                    break
                
                # Simple mouse wiggle
                page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                page.wait_for_timeout(1000)

            if not results:
                debug_info["status"] = "Timed out"
                debug_info["final_url"] = page.url
                # Capture text to see if we are still blocked
                try:
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
