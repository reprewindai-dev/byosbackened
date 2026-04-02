import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Router Console",
  description: "Drag-and-drop deployable AI Router (UI + Backend on Vercel)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
