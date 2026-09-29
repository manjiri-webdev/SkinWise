import "./globals.css";
import { ServerWarmup } from "@/components/ServerWarmup";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ServerWarmup />
        {children}
      </body>
    </html>
  );
}
