from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn

app = FastAPI()

def scrape_logic():
    # --- YOUR WORKING CODE GOES HERE ---
    results = []
    with sync_playwright() as p:
        # Use the exact headers you found worked
        my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
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
        
        def handle_response(response):
            if "/hezushon/ge/" in response.url:
                try:
                    results.append(response.json())
                except:
                    pass

        page.on("response", handle_response)
        
        try:
            # Short timeout because server time is expensive
            page.goto("https://vidfast.pro/movie/533535", wait_until="domcontentloaded")
            for _ in range(15):
                if len(results) >= 2: break
                page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Error: {e}")
            
        browser.close()
    return results

@app.get("/scrape")
def run_scraper():
    data = scrape_logic()
    if data:
        return {"status": "success", "data": data}
    return {"status": "failed", "message": "No data found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
