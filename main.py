from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn
import random

app = FastAPI()

def scrape_logic():
    results = []
    debug_info = {"status": "Starting"}
    
    with sync_playwright() as p:
        # 1. Use Honest Linux User Agent
        linux_user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu", 
            ]
        )

        context = browser.new_context(
            user_agent=linux_user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1"
            }
        )

        # --- THE GPU LIE (WebGL Spoofing) ---
        # We overwrite the browser function that reports the GPU model.
        # Instead of "SwiftShader" (Bot), we say "Intel Iris OpenGL" (Human).
        context.add_init_script("""
            // 1. Fake the GPU
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // 37445 = UNMASKED_VENDOR_WEBGL
                if (parameter === 37445) return 'Intel Open Source Technology Center';
                // 37446 = UNMASKED_RENDERER_WEBGL
                if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 620 (Kaby Lake GT2)';
                return getParameter(parameter);
            };

            // 2. Fake the "Permissions" API (Common headless giveaway)
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );

            // 3. Remove "WebDriver" flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()
        
        # --- LISTEN FOR FAILURES (New Debugging) ---
        # If the specific request is blocked (403), we want to know immediately.
        def handle_request_failed(request):
            if "/hezushon/ge/" in request.url:
                print(f"BLOCKED: {request.url} failed with {request.failure}")
                debug_info["block_reason"] = str(request.failure)

        page.on("requestfailed", handle_request_failed)

        def handle_response(response):
            if "/hezushon/ge/" in response.url:
                print(f"STATUS: {response.status} | URL: {response.url}")
                if response.status == 200:
                    try:
                        data = response.json()
                        if data not in results:
                            results.append(data)
                    except:
                        pass
                else:
                    debug_info["http_error"] = response.status

        page.on("response", handle_response)
        
        try:
            print("Navigating...")
            page.goto("https://vidfast.pro/movie/533535?autoplay=true", timeout=60000, wait_until="domcontentloaded")
            
            # --- INTERACTION LOOP ---
            debug_info["status"] = "Waiting..."
            for i in range(25):
                if len(results) >= 2:
                    break
                
                # Wiggle mouse to trigger "User Activity"
                page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                
                # Check if we are still stuck on "Fetching"
                try:
                    if i == 5: # Only check once after 5 seconds
                        if page.is_visible("text=FETCHING"):
                            print("Loader detected. Attempting to click it...")
                            page.click("body") # Blind click to focus
                except:
                    pass
                
                page.wait_for_timeout(1000)

            if not results:
                debug_info["status"] = "Timed out"
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
