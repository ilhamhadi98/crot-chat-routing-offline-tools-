import "./globals.css";

export const metadata = {
  title: "CROT [Chat Routing Offline Tools]",
  description: "Advanced Frontend for CROT Backend",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body data-theme="dark">{children}</body>
    </html>
  );
}
