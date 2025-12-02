# api/proxy.py
# Serverless Python using FastAPI + httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
import httpx
from urllib.parse import urljoin, quote

app = FastAPI()

@app.api_route("/api/proxy", methods=["GET", "OPTIONS"])
async def proxy(req: Request):
    # CORS preflight
    if req.method == "OPTIONS":
        return Response(status_code=204, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        })

    params = dict(req.query_params)
    target_url = params.get("url")
    origin = f"{req.url.scheme}://{req.url.netloc}"

    if not target_url:
        html = "<h1>Aurora Vercel Proxy (Python)</h1><p>Append <code>/api/proxy?url=...</code></p>"
        return HTMLResponse(content=html)

    if " " in target_url:
        target_url = target_url.replace(" ", "+")

    custom_referer = params.get("referer", "https://streameeeeee.site/")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Referer": custom_referer,
        "Origin": "https://streameeeeee.site",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            upstream = await client.get(target_url, headers=headers)

        if upstream.status_code == 403:
            return PlainTextResponse("Vercel IP Blocked (403)", status_code=403, headers={"Access-Control-Allow-Origin": "*"})

        # Copy headers (strip hop-by-hop)
        out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in ["content-length", "content-encoding", "transfer-encoding"]}
        out_headers["Access-Control-Allow-Origin"] = "*"
        content_type = upstream.headers.get("Content-Type", "")

        is_hls = ("application/vnd.apple.mpegurl" in content_type) or ("application/x-mpegURL" in content_type) or target_url.endswith(".m3u8")

        if is_hls:
            out_headers["Content-Type"] = "application/vnd.apple.mpegurl"
            text = upstream.text
            base = target_url

            # rewrite segments
            def repl_line(match: str):
                line = match.group(0)
                if line.startswith("#"):  # do not rewrite comments
                    return line
                seg = line.strip()
                if not seg:
                    return line
                absolute = urljoin(base, seg)
                return f"{origin}/api/proxy?url={quote(absolute, safe='')}&referer={quote(custom_referer, safe='')}"

            import re
            text = re.sub(r"^(.*)$", repl_line, text, flags=re.M)

            # rewrite key URIs
            def repl_key(m):
                q1, uri, q3 = m.group(1), m.group(2), m.group(3)
                absolute = urljoin(base, uri)
                return f'URI={q1}{origin}/api/proxy?url={quote(absolute, safe="")}&referer={quote(custom_referer, safe="")}{q3}'
            text = re.sub(r'URI=(["\']?)([^"\',\s]+)(["\']?)', repl_key, text)

            return Response(content=text, media_type="application/vnd.apple.mpegurl", headers=out_headers)

        # binary tweaks
        if (".ts" in target_url) or ("video/MP2T" in content_type):
            out_headers["Content-Type"] = "video/MP2T"

        return Response(content=upstream.content, status_code=upstream.status_code, headers=out_headers)
    except Exception as e:
        return PlainTextResponse(f"Vercel Error: {str(e)}", status_code=500, headers={"Access-Control-Allow-Origin": "*"})
