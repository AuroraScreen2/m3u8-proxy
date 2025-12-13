from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import time

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"title": "Unknown", "url": "Unknown"}
    
    with sync_playwright() as p:
        # User Agent & Headers (Matches your curl)
        my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        
        # Launch with extra stealth arguments for Linux
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox"
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

        page = context.new_page()
        
        # Listener
        def handle_response(response):
            if "/hezushon/ge/" in response.url:
                try:
                    data = response.json()
                    results.append(data)
                except:
                    pass

        page.on("response", handle_response)
        
        try:
            print("Navigating...")
            # Increased timeout to 60s for slow servers
            page.goto("https://vidfast.pro/movie/533535", wait_until="domcontentloaded", timeout=60000)
            
            # Wait up to 45 seconds
            for i in range(45):
                if len(results) >= 2:
                    break
                page.wait_for_timeout(1000)
            
            # Capture debug info if we failed
            if not results:
                debug_info["title"] = page.title()
                debug_info["url"] = page.url
                # Get first 200 chars of body text to check for "Access Denied"
                try:
                    debug_info["content_snippet"] = page.inner_text("body")[:200]
                except:
                    debug_info["content_snippet"] = "Could not read body"

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
    
    # This will tell us WHY it failed
    return {
        "status": "failed", 
        "message": "No data found", 
        "debug": debug
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
