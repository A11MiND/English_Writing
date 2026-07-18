import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "English AI Writing Platform",
  description: "School-based English AI writing, assessment and reporting platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
