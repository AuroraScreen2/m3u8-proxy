export const metadata = {
  title: "Aurora Vercel Proxy",
  description: "Edge HLS proxy demo"
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "ui-sans-serif, system-ui", margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
