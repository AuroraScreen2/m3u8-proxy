export const config = { runtime: "edge" };

export default async function handler(request) {
  const url = new URL(request.url);
  const workerOrigin = url.origin;

  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
      },
    });
  }

  let targetUrl = url.searchParams.get("url");
  if (!targetUrl) {
    return new Response(
      `<h1>Aurora Vercel Proxy</h1><p>Use: <code>${workerOrigin}/api/proxy?url=&lt;ENCODED&gt;&referer=&lt;optional&gt;</code></p>`,
      { headers: { "Content-Type": "text/html" } }
    );
  }

  if (targetUrl.includes(" ")) targetUrl = targetUrl.replace(/ /g, "+");

  const customReferer = url.searchParams.get("referer") || "https://streameeeeee.site/";
  const customOrigin = "https://streameeeeee.site";

  const proxyHeaders = new Headers({
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    Referer: customReferer,
    Origin: customOrigin,
    Accept: "*/*",
    Connection: "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
  });

  try {
    const resp = await fetch(targetUrl, { method: "GET", headers: proxyHeaders, redirect: "follow" });
    if (resp.status === 403) return new Response("Vercel IP Blocked (403)", { status: 403 });

    const out = new Headers(resp.headers);
    out.delete("Content-Length");
    out.delete("Content-Encoding");
    out.delete("Transfer-Encoding");
    out.set("Access-Control-Allow-Origin", "*");

    const ct = out.get("Content-Type") || "";
    const isHls =
      ct.includes("application/vnd.apple.mpegurl") ||
      ct.includes("application/x-mpegURL") ||
      targetUrl.endsWith(".m3u8");

    if (isHls) {
      out.set("Content-Type", "application/vnd.apple.mpegurl");
      const baseUrl = targetUrl;
      let text = await resp.text();

      // rewrite segments
      text = text.replace(/^(?!#)(.*)$/gm, (line) => {
        const seg = line.trim();
        if (!seg) return line;
        const abs = new URL(seg, baseUrl).href;
        return `${workerOrigin}/api/proxy?url=${encodeURIComponent(abs)}&referer=${encodeURIComponent(customReferer)}`;
      });

      // rewrite key URIs
      text = text.replace(/URI=(["']?)([^"',\s]+)(["']?)/g, (_m, q1, uri, q3) => {
        const abs = new URL(uri, baseUrl).href;
        return `URI=${q1}${workerOrigin}/api/proxy?url=${encodeURIComponent(abs)}&referer=${encodeURIComponent(
          customReferer
        )}${q3}`;
      });

      return new Response(text, { status: 200, headers: out });
    }

    if (targetUrl.includes(".ts") || ct.includes("video/MP2T")) out.set("Content-Type", "video/MP2T");

    return new Response(resp.body, { status: resp.status, headers: out });
  } catch (e) {
    return new Response(`Vercel Error: ${e?.message ?? "Unknown error"}`, { status: 500 });
  }
}
