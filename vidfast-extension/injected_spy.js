(function() {
    console.log("M3U8 Sniffer Active...");

    // Helper to send data
    function broadcastFound(url) {
        window.postMessage({ 
            type: "M3U8_FOUND", 
            payload: url
        }, "*");
    }

    // 1. Intercept XMLHttpRequest (Used by HLS.js players)
    const XHR = XMLHttpRequest.prototype;
    const open = XHR.open;
    const send = XHR.send;

    XHR.open = function(method, url) {
        this._url = url; 
        return open.apply(this, arguments);
    };

    XHR.send = function(postData) {
        // Check URL immediately when request is sent
        if (this._url && 
            this._url.includes("p.10014.workers.dev") && 
            this._url.includes(".m3u8")) {
                console.log("Found M3U8 (XHR):", this._url);
                broadcastFound(this._url);
        }
        return send.apply(this, arguments);
    };

    // 2. Intercept Fetch API (Used by newer players)
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        let url = args[0];
        // Handle if URL is inside a Request object
        if (typeof url === 'object' && url.url) {
            url = url.url;
        }

        if (url && 
            url.includes("p.10014.workers.dev") && 
            url.includes(".m3u8")) {
                console.log("Found M3U8 (Fetch):", url);
                broadcastFound(url);
        }
        
        return originalFetch(...args);
    };
})();