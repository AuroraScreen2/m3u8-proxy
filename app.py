from flask import Flask, request, Response, stream_with_context
import requests
from urllib.parse import urljoin, quote
import urllib3
import re
import os  # <--- REQUIRED FOR RENDER

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- CONFIGURATION ---
# Render provides the port in the environment variables. 
# If running locally, it defaults to 5000.
PORT = int(os.environ.get("PORT", 5000))

DEFAULT_REFERER = "https://streameeeeee.site/"
DEFAULT_ORIGIN = "https://streameeeeee.site"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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
    if not target_url: 
        return "Error: No URL provided.", 400

    if ' ' in target_url: target_url = target_url.replace(' ', '+')

    current_referer = request.args.get('referer', DEFAULT_REFERER)
    
    # Dynamic Host Detection
    proxy_root = request.url_root

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": current_referer,
        "Origin": DEFAULT_ORIGIN,
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    try:
        resp = requests.get(target_url, headers=headers, stream=True, verify=False, timeout=15)
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'host']
        headers_to_send = [
            (name, value) for (name, value) in resp.headers.items()
            if name.lower() not in excluded_headers
        ]
        headers_to_send.append(('Access-Control-Allow-Origin', '*'))

        content_type = resp.headers.get('Content-Type', '').lower()

        # M3U8 REWRITE LOGIC
        if target_url.endswith('.m3u8') or 'mpegurl' in content_type or 'application/x-mpegurl' in content_type:
            content = resp.text
            base_url = target_url
            
            def make_proxy_url(match):
                original = match.group(1).strip()
                if not original: return match.group(0)

                quote_char = ""
                if original.startswith('"') and original.endswith('"'):
                    quote_char = '"'
                    original = original[1:-1]
                
                absolute_url = urljoin(base_url, original)
                encoded_url = quote(absolute_url)
                encoded_referer = quote(current_referer)
                
                return f'{quote_char}{proxy_root}proxy?url={encoded_url}&referer={encoded_referer}{quote_char}'

            new_content = re.sub(r'^(?!#)(\S+)$', make_proxy_url, content, flags=re.MULTILINE)
            
            new_content = re.sub(r'URI=(["\']?)([^",\s]+)(["\']?)', 
                                 lambda m: f'URI={m.group(1)}{proxy_root}proxy?url={quote(urljoin(base_url, m.group(2)))}&referer={quote(current_referer)}{m.group(3)}', 
                                 new_content)

            return Response(new_content, status=resp.status_code, headers=headers_to_send)

        # BINARY STREAM
        return Response(stream_with_context(resp.iter_content(chunk_size=65536)), 
                        status=resp.status_code, 
                        content_type=content_type,
                        direct_passthrough=True,
                        headers=headers_to_send)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"Proxy Error: {e}", 500

if __name__ == '__main__':
    # This block is only run when testing locally.
    # On Render, Gunicorn will handle the execution.
    app.run(host='0.0.0.0', port=PORT)
