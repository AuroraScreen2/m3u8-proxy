# FILE: api/proxy.js
export const config = {
  runtime: "edge", // critical for streaming
};

export default async function handler(request) {
  const url = new URL(request.url);
  const workerOrigin = url.origin;

  // 1) CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
      },
    });
  }

  // 2) Simple UI helper
  let targetUrl = url.searchParams.get("url");
  if (!targetUrl) {
    return new Response(renderGenerator(workerOrigin), {
      headers: { "Content-Type": "text/html" },
    });
  }

  // 3) Auto-fix spaces
  if (targetUrl.includes(" ")) {
    targetUrl = targetUrl.replace(/ /g, "+");
  }

  // 4) Upstream headers
  const customReferer = url.searchParams.get("referer") || "https://streameeeeee.site/";
  const customOrigin = "https://streameeeeee.site";

  const proxyHeaders = new Headers();
  proxyHeaders.set(
    "User-Agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
  );
  proxyHeaders.set("Referer", customReferer);
  proxyHeaders.set("Origin", customOrigin);
  proxyHeaders.set("Accept", "*/*");
  proxyHeaders.set("Connection", "keep-alive");
  // Anti-bot signals (why: some CDNs check these)
  proxyHeaders.set("Sec-Fetch-Dest", "empty");
  proxyHeaders.set("Sec-Fetch-Mode", "cors");
  proxyHeaders.set("Sec-Fetch-Site", "cross-site");

  try {
    // 5) Fetch upstream
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: proxyHeaders,
      redirect: "follow",
    });

    // Edge egress blocked
    if (response.status === 403) {
      return new Response("Vercel IP Blocked (403)", { status: 403 });
    }

    // 6) Sanitize headers
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("Content-Length");
    responseHeaders.delete("Content-Encoding");
    responseHeaders.delete("Transfer-Encoding");
    responseHeaders.set("Access-Control-Allow-Origin", "*");

    const contentType = responseHeaders.get("Content-Type") || "";

    // 7) HLS playlist rewrite
    const isHls =
      contentType.includes("application/vnd.apple.mpegurl") ||
      contentType.includes("application/x-mpegURL") ||
      targetUrl.endsWith(".m3u8");

    if (isHls) {
      responseHeaders.set("Content-Type", "application/vnd.apple.mpegurl");
      let text = await response.text();
      const baseUrl = targetUrl;

      // Rewrite TS/playlist URIs (non-comment lines)
      text = text.replace(/^(?!#)(.*)$/gm, (line) => {
        const originalSegment = line.trim();
        if (!originalSegment) return line;
        const absoluteUrl = new URL(originalSegment, baseUrl).href;
        const encodedUrl = encodeURIComponent(absoluteUrl);
        const encodedReferer = encodeURIComponent(customReferer);
        return `${workerOrigin}/api/proxy?url=${encodedUrl}&referer=${encodedReferer}`;
      });

      // Rewrite key URIs
      text = text.replace(/URI=(["']?)([^"',\s]+)(["']?)/g, (_m, q1, uri, q3) => {
        const absoluteKey = new URL(uri, baseUrl).href;
        const encodedKey = encodeURIComponent(absoluteKey);
        const encodedRef = encodeURIComponent(customReferer);
        return `URI=${q1}${workerOrigin}/api/proxy?url=${encodedKey}&referer=${encodedRef}${q3}`;
      });

      return new Response(text, { status: 200, headers: responseHeaders });
    }

    // 8) Binary passthrough tweaks
    if (targetUrl.includes(".ts") || contentType.includes("video/MP2T")) {
      responseHeaders.set("Content-Type", "video/MP2T"); // why: ensure correct MIME for HLS segments
    }

    // Stream original body
    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (err) {
    return new Response(`Vercel Error: ${err?.message ?? "Unknown error"}`, { status: 500 });
  }
}

function renderGenerator(origin) {
  return `<h1>Aurora Vercel Proxy</h1><p>Use: <code>${origin}/api/proxy?url=&lt;ENCODED&gt;&referer=&lt;optional&gt;</code></p>`;
}
