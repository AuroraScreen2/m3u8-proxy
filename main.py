from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import time

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"title": "Unknown", "url": "Unknown", "status": "Starting"}
    
    with sync_playwright() as p:
        # 1. Use your exact User Agent
        my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        
        # 2. Launch Browser (Headless)
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
            user_agent=my_user_agent,
            viewport={"width": 1920, "height": 1080},
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

        # 3. CRITICAL: Manually delete the 'webdriver' property
        # This is the "Mask" that worked on your local PC.
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
                    # Only add if we haven't seen this exact one before
                    if data not in results:
                        results.append(data)
                except:
                    pass

        page.on("response", handle_response)
        
        try:
            print("Navigating...")
            # Go to the page
            page.goto("https://vidfast.pro/movie/533535", timeout=60000, wait_until="domcontentloaded")
            
            # 4. EXPLICITLY WAIT FOR THE LOADER TO GO AWAY
            # We wait up to 10 seconds for the text "FETCHING" to disappear.
            try:
                debug_info["status"] = "Waiting for loader to vanish..."
                # This regex matches "FETCHING" case-insensitive
                page.wait_for_selector("text=/FETCHING/i", state="detached", timeout=15000)
                debug_info["status"] = "Loader finished."
            except:
                debug_info["status"] = "Loader stuck (timed out)."

            # Now wait for data
            for i in range(30):
                if len(results) >= 2:
                    break
                page.wait_for_timeout(1000)
            
            # Collect Debug Info
            if not results:
                debug_info["title"] = page.title()
                debug_info["url"] = page.url
                try:
                    # Get the main text of the body to see what we are stuck on
                    debug_info["content_snippet"] = page.inner_text("body")[:300]
                except:
                    debug_info["content_snippet"] = "Body empty"

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
