// Inject the spy script
var s = document.createElement('script');
s.src = chrome.runtime.getURL('injected_spy.js');
s.onload = function() { this.remove(); };
(document.head || document.documentElement).appendChild(s);

// Listen for the m3u8 link
window.addEventListener("message", function(event) {
    if (event.source != window) return;

    if (event.data.type && (event.data.type == "M3U8_FOUND")) {
        console.log("Extension Captured M3U8:", event.data.payload);
        
        // Save to storage (overwriting old data)
        chrome.storage.local.set({ 
            "captured_m3u8": event.data.payload 
        });
    }
});