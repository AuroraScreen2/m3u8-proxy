export const config = {
  runtime: 'edge', // This is critical for streaming video
};

export default async function handler(request) {
  const url = new URL(request.url);
  const workerOrigin = url.origin;

  // --- 1. HANDLE CORS PRE-FLIGHT ---
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
      },
    });
  }

  // --- 2. LINK GENERATOR (UI) ---
  let targetUrl = url.searchParams.get("url");
  if (!targetUrl) {
    return new Response(renderGenerator(workerOrigin), {
      headers: { "Content-Type": "text/html" },
    });
  }

  // --- 3. AUTO-FIX SPACES ---
  if (targetUrl.includes(" ")) {
    targetUrl = targetUrl.replace(/ /g, "+");
  }

  // --- 4. MASTER KEY HEADERS ---
  const customReferer = url.searchParams.get("referer") || "https://streameeeeee.site/";
  const customOrigin = "https://streameeeeee.site";

  const proxyHeaders = new Headers();
  proxyHeaders.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36");
  proxyHeaders.set("Referer", customReferer);
  proxyHeaders.set("Origin", customOrigin);
  proxyHeaders.set("Accept", "*/*");
  proxyHeaders.set("Connection", "keep-alive");
  
  // Anti-Bot Headers
  proxyHeaders.set("Sec-Fetch-Dest", "empty");
  proxyHeaders.set("Sec-Fetch-Mode", "cors");
  proxyHeaders.set("Sec-Fetch-Site", "cross-site");

  try {
    // --- 5. FETCH ---
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: proxyHeaders,
      redirect: "follow",
    });

    // CHECK FOR 403
    if (response.status === 403) {
        // If this happens, Vercel IPs are also blocked
        return new Response("Vercel IP Blocked (403)", { status: 403 });
    }

    // --- 6. HEADER STRIPPING ---
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("Content-Length");
    responseHeaders.delete("Content-Encoding");
    responseHeaders.delete("Transfer-Encoding");
    responseHeaders.set("Access-Control-Allow-Origin", "*");

    const contentType = responseHeaders.get("Content-Type") || "";

    // --- 7. M3U8 REWRITE LOGIC ---
    if (
      contentType.includes("application/vnd.apple.mpegurl") ||
      contentType.includes("application/x-mpegURL") ||
      targetUrl.endsWith(".m3u8")
    ) {
      responseHeaders.set("Content-Type", "application/vnd.apple.mpegurl");
      let text = await response.text();
      const baseUrl = targetUrl;

      // Rewrite Segments
      text = text.replace(/^(?!#)(.*)$/gm, (match) => {
        const originalSegment = match.trim();
        if (!originalSegment) return match;
        const absoluteUrl = new URL(originalSegment, baseUrl).href;
        const encodedUrl = encodeURIComponent(absoluteUrl);
        const encodedReferer = encodeURIComponent(customReferer);
        return `${workerOrigin}/api/proxy?url=${encodedUrl}&referer=${encodedReferer}`;
      });

      // Rewrite Keys
      text = text.replace(/URI=(["']?)([^"',\s]+)(["']?)/g, (match, q1, uri, q3) => {
          const absoluteKey = new URL(uri, baseUrl).href;
          const encodedKey = encodeURIComponent(absoluteKey);
          const encodedRef = encodeURIComponent(customReferer);
          return `URI=${q1}${workerOrigin}/api/proxy?url=${encodedKey}&referer=${encodedRef}${q3}`;
      });

      return new Response(text, { status: 200, headers: responseHeaders });
    }

    // --- 8. BINARY PASSTHROUGH ---
    if (targetUrl.includes(".ts") || contentType.includes("video/MP2T")) {
        responseHeaders.set("Content-Type", "video/MP2T");
    }

    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });

  } catch (err) {
    return new Response(`Vercel Error: ${err.message}`, { status: 500 });
  }
}

function renderGenerator(origin) {
    return `<h1>Aurora Vercel Proxy</h1><p>Append <code>/api/proxy?url=...</code> to use.</p>`;
}
