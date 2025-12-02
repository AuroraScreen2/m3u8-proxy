from flask import Flask, request, Response, stream_with_context, render_template_string
import requests
from urllib.parse import urljoin, quote
import urllib3
import re

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

PORT = 5000
# MASTER KEY HEADERS
DEFAULT_REFERER = "https://streameeeeee.site/"
DEFAULT_ORIGIN = "https://streameeeeee.site"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

@app.route('/')
def index():
    return render_template_string('''
        <html>
        <body style="font-family:sans-serif; padding:40px; background:#111; color:white;">
            <div style="background:#222; padding:30px; border-radius:8px; max-width:800px; margin:0 auto; border:1px solid #444;">
                <h2 style="color:#00ff99;">Aurora Proxy v5 (Header Stripper)</h2>
                <input type="text" id="targetUrl" placeholder="Paste m3u8 link here" style="width:100%; padding:12px; background:#333; color:white; border:1px solid #555;">
                <br><br>
                <button onclick="generate()" style="padding:12px 24px; background:#00ff99; color:black; font-weight:bold; border:none; cursor:pointer;">GENERATE LINK</button>
                <div id="result" style="margin-top:20px; word-break:break-all; background:#000; padding:15px; display:none; border:1px solid #00ff99; color:#00ff99; font-family:monospace;"></div>
            </div>
            <script>
                function generate() {
                    let input = document.getElementById('targetUrl').value.trim();
                    if (!input) return;
                    const finalUrl = `http://localhost:5000/proxy?url=${encodeURIComponent(input)}`;
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerText = finalUrl;
                }
            </script>
        </body>
        </html>
    ''')

@app.route('/proxy', methods=['GET', 'OPTIONS'])
def proxy():
    # 1. Handle CORS Pre-flight (Browser Security)
    if request.method == 'OPTIONS':
        return Response("", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        })

    target_url = request.args.get('url')
    if not target_url: return "Missing URL", 400

    # Auto-Repair Spaces in URL
    if ' ' in target_url: target_url = target_url.replace(' ', '+')

    current_referer = request.args.get('referer', DEFAULT_REFERER)

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": current_referer,
        "Origin": DEFAULT_ORIGIN,
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    try:
        # Request with stream=True
        resp = requests.get(target_url, headers=headers, stream=True, verify=False, timeout=10)
        
        # 2. SANITIZE HEADERS (The Fix)
        # We MUST NOT forward Content-Length or Content-Encoding from the source.
        # Flask/Browser must recalculate these because we might modify the body.
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_to_send = [
            (name, value) for (name, value) in resp.headers.items()
            if name.lower() not in excluded_headers
        ]
        # Force CORS on every response
        headers_to_send.append(('Access-Control-Allow-Origin', '*'))

        content_type = resp.headers.get('Content-Type', '')

        # 3. M3U8 REWRITE LOGIC
        if target_url.endswith('.m3u8') or 'mpegurl' in content_type:
            # We must read the whole content to rewrite it
            content = resp.text # request.text auto-handles gzip decompression
            base_url = target_url
            
            def make_proxy_url(match):
                original = match.group(1)
                quote_char = ""
                if original.startswith('"') and original.endswith('"'):
                    quote_char = '"'
                    original = original[1:-1]
                
                absolute_url = urljoin(base_url, original)
                encoded_url = quote(absolute_url)
                encoded_referer = quote(current_referer)
                return f'{quote_char}http://localhost:{PORT}/proxy?url={encoded_url}&referer={encoded_referer}{quote_char}'

            # Rewrite Segments
            new_content = re.sub(r'^(?!#)(.*)$', make_proxy_url, content, flags=re.MULTILINE)
            # Rewrite Keys
            new_content = re.sub(r'URI=(["\']?)([^",\s]+)(["\']?)', 
                                 lambda m: f'URI={m.group(1)}http://localhost:{PORT}/proxy?url={quote(urljoin(base_url, m.group(2)))}&referer={quote(current_referer)}{m.group(3)}', 
                                 new_content)

            return Response(new_content, status=resp.status_code, headers=headers_to_send)

        # 4. BINARY STREAM (Segments/Keys)
        # direct_passthrough=True ensures Flask doesn't try to buffer or mess with the bytes
        return Response(stream_with_context(resp.iter_content(chunk_size=8192)), 
                        status=resp.status_code, 
                        content_type=content_type,
                        direct_passthrough=True,
                        headers=headers_to_send)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"Proxy Error: {e}", 500

if __name__ == '__main__':
    print(f"🚀 Proxy v5 running on http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
