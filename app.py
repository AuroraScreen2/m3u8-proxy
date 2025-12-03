from flask import Flask, request, Response, stream_with_context
from curl_cffi import requests as crequests # <--- The Magic Library
from urllib.parse import urljoin, quote
import re
import os

app = Flask(__name__)

# --- CONFIGURATION ---
PORT = int(os.environ.get("PORT", 5000))
DEFAULT_REFERER = "https://streameeeeee.site/"
DEFAULT_ORIGIN = "https://streameeeeee.site"

# We don't need a fake User-Agent string anymore. 
# curl_cffi handles that internally by impersonating Chrome.

@app.route('/proxy', methods=['GET', 'OPTIONS'])
def proxy():
    # 1. Handle CORS
    if request.method == 'OPTIONS':
        return Response("", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        })

    target_url = request.args.get('url')
    if not target_url: return "Error: No URL provided.", 400

    if ' ' in target_url: target_url = target_url.replace(' ', '+')
    current_referer = request.args.get('referer', DEFAULT_REFERER)
    proxy_root = request.url_root

    headers = {
        "Referer": current_referer,
        "Origin": DEFAULT_ORIGIN,
    }

    try:
        # --- THE FIX: IMPERSONATE CHROME ---
        # "impersonate='chrome124'" makes Cloudflare think this is a real browser
        resp = crequests.get(
            target_url, 
            headers=headers, 
            impersonate="chrome124", 
            stream=True, 
            timeout=15
        )

        # 2. ERROR CHECKING (Prevent the "Messy Text")
        # If Cloudflare blocks us, resp.status_code will likely be 403 or 503.
        # We should forward that error instead of trying to rewrite it.
        if resp.status_code in [403, 503, 429]:
            return Response(f"Cloudflare Blocked Request. Status: {resp.status_code}", status=resp.status_code)

        # 3. SANITIZE HEADERS
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'host']
        headers_to_send = [
            (name, value) for (name, value) in resp.headers.items()
            if name.lower() not in excluded_headers
        ]
        headers_to_send.append(('Access-Control-Allow-Origin', '*'))

        content_type = resp.headers.get('Content-Type', '').lower()

        # 4. M3U8 REWRITE LOGIC
        # Added a check to ensure we aren't rewriting HTML error pages
        is_m3u8 = target_url.endswith('.m3u8') or 'mpegurl' in content_type or 'application/x-mpegurl' in content_type
        
        if is_m3u8 and '<html' not in resp.text[:100].lower():
            content = resp.text
            base_url = target_url
            
            def make_proxy_url(match):
                original = match.group(1).strip()
                if not original or original.startswith('#'): return match.group(0)

                # Stop regex from grabbing HTML tags if they sneak in
                if original.startswith('<'): return match.group(0)

                quote_char = ""
                if original.startswith('"') and original.endswith('"'):
                    quote_char = '"'
                    original = original[1:-1]
                
                absolute_url = urljoin(base_url, original)
                encoded_url = quote(absolute_url)
                encoded_referer = quote(current_referer)
                
                return f'{quote_char}{proxy_root}proxy?url={encoded_url}&referer={encoded_referer}{quote_char}'

            # Rewrites Segments
            new_content = re.sub(r'^(?!#)(\S+)$', make_proxy_url, content, flags=re.MULTILINE)
            
            # Rewrites Keys
            new_content = re.sub(r'URI=(["\']?)([^",\s]+)(["\']?)', 
                                 lambda m: f'URI={m.group(1)}{proxy_root}proxy?url={quote(urljoin(base_url, m.group(2)))}&referer={quote(current_referer)}{m.group(3)}', 
                                 new_content)

            return Response(new_content, status=resp.status_code, headers=headers_to_send)

        # 5. BINARY STREAM
        return Response(stream_with_context(resp.iter_content(chunk_size=65536)), 
                        status=resp.status_code, 
                        content_type=content_type,
                        direct_passthrough=True,
                        headers=headers_to_send)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"Proxy Error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
