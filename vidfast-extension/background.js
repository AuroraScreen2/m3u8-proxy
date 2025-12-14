// YOUR CLOUDFLARE WORKER URL
const WORKER_ENDPOINT = "https://pong.aurorascreen.workers.dev";

// Filter out these domains (Add more if needed)
const IGNORED_DOMAINS = [
    "youtube.com",
    "googlevideo.com",
    "twitch.tv",
    "netflix.com"
];

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        const url = details.url;
        
        // 1. CHECK: Is it an m3u8?
        if (url.toLowerCase().indexOf(".m3u8") === -1) return;

        // 2. CHECK: Is it a "bad" domain?
        if (IGNORED_DOMAINS.some(domain => url.includes(domain))) return;

        // 3. CHECK: Have we already sent this recently? (Avoid spamming)
        // We use the tab ID + URL as a unique key
        const cacheKey = `sent_${details.tabId}_${url}`;
        
        chrome.storage.local.get([cacheKey], function(result) {
            if (!result[cacheKey]) {
                
                // --- NEW LINK FOUND! ---
                console.log("🚀 SENDING TO WORKER:", url);

                // Get the page URL (the movie page user is looking at)
                chrome.tabs.get(details.tabId, function(tab) {
                    const pageUrl = tab ? tab.url : "unknown";

                    // Send to Cloudflare
                    fetch(WORKER_ENDPOINT, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            movie_url: pageUrl,
                            stream_url: url
                        })
                    }).catch(err => console.error("Upload failed", err));
                    
                    // Mark as sent so we don't send it 50 times a second
                    let saveObj = {};
                    saveObj[cacheKey] = true;
                    chrome.storage.local.set(saveObj);
                });
            }
        });
    },
    { urls: ["<all_urls>"] }
);