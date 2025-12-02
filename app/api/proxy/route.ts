// app/api/proxy/route.ts
export const runtime = "edge";

function helper(origin: string) {
  return `<h1>Aurora Vercel Proxy</h1>
<p>Use: <code>${origin}/api/proxy?url=&lt;ENCODED_TARGET&gt;&amp;referer=&lt;optional&gt;</code></p>`;
}

function corsHeaders(extra?: HeadersInit) {
  const h = new Headers(extra);
  h.set("Access-Control-Allow-Origin", "*");
  h.set("Access-Control-Allow-Methods", "GET, OPTIONS");
  h.set("Access-Control-Allow-Headers", "*");
  return h;
}

function sanitizeHeaders(h: Headers) {
  const out = new Headers(h);
  out.delete("Content-Length");
  out.delete("Content-Encoding");
  out.delete("Transfer-Encoding");
  out.set("Access-Control-Allow-Origin", "*");
  return out;
}

function isHls(contentType: string, url: string) {
  return (
    contentType.includes("application/vnd.apple.mpegurl") ||
    contentType.includes("application/x-mpegURL") ||
    url.endsWith(".m3u8")
  );
}

export async function OPTIONS() {
  return new Response(null, { headers: corsHeaders() });
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const origin = url.origin;

  let targetUrl = url.searchParams.get("url");
  if (!targetUrl) {
    return new Response(helper(origin), { headers: { "Content-Type": "text/html" } });
  }

  if (targetUrl.includes(" ")) targetUrl = targetUrl.replace(/ /g, "+");

  const customReferer = url.searchParams.get("referer") || "https://streameeeeee.site/";
  const customOrigin = "https://streameeeeee.site";

  const upstreamHeaders = new Headers();
  upstreamHeaders.set(
    "User-Agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
  );
  upstreamHeaders.set("Accept", "*/*");
  upstreamHeaders.set("Referer", customReferer);
  upstreamHeaders.set("Origin", customOrigin);
  upstreamHeaders.set("Connection", "keep-alive");
  upstreamHeaders.set("Sec-Fetch-Dest", "empty");
  upstreamHeaders.set("Sec-Fetch-Mode", "cors");
  upstreamHeaders.set("Sec-Fetch-Site", "cross-site");

  try {
    const res = await fetch(targetUrl, {
      method: "GET",
      headers: upstreamHeaders,
      redirect: "follow"
    });

    if (res.status === 403) {
      return new Response("Vercel IP Blocked (403)", { status: 403 });
    }

    const outHeaders = sanitizeHeaders(res.headers);
    const contentType = outHeaders.get("Content-Type") || "";

    if (isHls(contentType, targetUrl)) {
      outHeaders.set("Content-Type", "application/vnd.apple.mpegurl");
      const baseUrl = targetUrl;
      let text = await res.text();

      // rewrite segment lines (non-comment)
      text = text.replace(/^(?!#)(.*)$/gm, (line) => {
        const seg = line.trim();
        if (!seg) return line;
        const absolute = new URL(seg, baseUrl).href;
        const encodedUrl = encodeURIComponent(absolute);
        const encodedRef = encodeURIComponent(customReferer);
        return `${origin}/api/proxy?url=${encodedUrl}&referer=${encodedRef}`;
      });

      // rewrite key URIs
      text = text.replace(/URI=(["']?)([^"',\s]+)(["']?)/g, (_m, q1, uri, q3) => {
        const absolute = new URL(uri, baseUrl).href;
        const encodedUrl = encodeURIComponent(absolute);
        const encodedRef = encodeURIComponent(customReferer);
        return `URI=${q1}${origin}/api/proxy?url=${encodedUrl}&referer=${encodedRef}${q3}`;
      });

      return new Response(text, { status: 200, headers: outHeaders });
    }

    if (targetUrl.includes(".ts") || contentType.includes("video/MP2T")) {
      outHeaders.set("Content-Type", "video/MP2T"); // why: some origins mislabel
    }

    return new Response(res.body, { status: res.status, headers: outHeaders });
  } catch (err: any) {
    return new Response(`Vercel Error: ${err?.message ?? "Unknown error"}`, { status: 500 });
  }
}
