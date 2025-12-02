"use client";
import { useCallback, useMemo, useRef, useState } from "react";
export default function Page() {
  const [src, setSrc] = useState("");
  const [referer, setReferer] = useState("");
  const [proxyUrl, setProxyUrl] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsCdn = "https://cdn.jsdelivr.net/npm/hls.js@1.5.14/dist/hls.min.js";
  const buildProxyUrl = useCallback((raw: string, ref?: string) => {
    if (!raw) return "";
    const url = new URL(window.location.href);
    url.pathname = "/api/proxy";
    url.searchParams.set("url", encodeURIComponent(raw));
    if (ref && ref.trim()) url.searchParams.set("referer", ref.trim());
    return url.toString();
  }, []);
  const onPreview = useCallback(async () => {
    const p = buildProxyUrl(src, referer);
    setProxyUrl(p);
    const video = videoRef.current;
    if (!video) return;
    const hasNative = video.canPlayType("application/vnd.apple.mpegurl");
    if (hasNative) {
      video.src = p;
      await video.play().catch(() => {});
      return;
    }
    // @ts-expect-error global load
    if (!window.Hls) {
      await new Promise<void>((resolve, reject) => {
        const s = document.createElement("script");
        s.src = hlsCdn;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error("Failed to load hls.js"));
        document.head.appendChild(s);
      });
    }
    // @ts-expect-error global
    const Hls = window.Hls;
    if (Hls.isSupported()) {
      const hls = new Hls({ lowLatencyMode: true });
      hls.loadSource(p);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
    } else {
      alert("HLS not supported on this browser.");
    }
  }, [src, referer, buildProxyUrl, hlsCdn]);
  const exampleLink = useMemo(
    () =>
      proxyUrl
        ? proxyUrl
        : src
        ? buildProxyUrl(src, referer)
        : "/api/proxy?url=https%253A%252F%252Ftest-streams.mux.dev%252Fx36xhzz%252Fx36xhzz.m3u8",
    [proxyUrl, src, referer, buildProxyUrl]
  );
  return (
    <main style={{ maxWidth: 920, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: "1.6rem", marginBottom: "0.75rem" }}>Aurora Vercel Proxy (Edge)</h1>
      <p style={{ marginTop: 0 }}>Paste an HLS <code>.m3u8</code> URL and optional Referer. Click Preview.</p>
      <div style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "1fr", marginTop: "1rem" }}>
        <label>
          <div>HLS URL</div>
          <input value={src} onChange={(e) => setSrc(e.target.value)} placeholder="https://example.com/playlist.m3u8" style={{ width: "100%", padding: "0.6rem" }} />
        </label>
        <label>
          <div>Referer (optional)</div>
          <input value={referer} onChange={(e) => setReferer(e.target.value)} placeholder="https://your-referer.example" style={{ width: "100%", padding: "0.6rem" }} />
        </label>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={onPreview} style={{ padding: "0.6rem 1rem", border: "1px solid #ddd", borderRadius: 8, cursor: "pointer" }}>Preview</button>
          <a href={exampleLink} target="_blank" rel="noreferrer" style={{ padding: "0.6rem 1rem", border: "1px solid #ddd", borderRadius: 8, textDecoration: "none" }}>
            Open raw playlist
          </a>
        </div>
      </div>
      <section style={{ marginTop: "1.25rem" }}>
        <video ref={videoRef} controls playsInline style={{ width: "100%", maxHeight: 480, background: "#000" }} />
      </section>
      <p style={{ fontSize: 12, color: "#666", marginTop: "1rem" }}>Use only with content you have rights to access. Some origins block Vercel egress; the API returns 403.</p>
    </main>
  );
}
