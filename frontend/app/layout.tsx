import type { Metadata } from "next";

import "./globals.css";

import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: "Illinois Front Office",
  description: "Basketball operations platform for recruiting, scouting, and roster construction.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>): JSX.Element {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
