import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Auto-Annotation Console",
  description: "Foundation-Model Auto-Annotation Pipeline",
};

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/datasets", label: "Datasets" },
  { href: "/jobs", label: "Jobs" },
  { href: "/reviews", label: "Review Queue" },
  { href: "/analytics", label: "Analytics" },
  { href: "/admin", label: "Admin" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <aside className="w-60 shrink-0 bg-white border-r border-gray-200 p-4">
              <h1 className="text-lg font-bold text-brand mb-6">Auto-Annotation</h1>
              <nav className="space-y-1">
                {NAV.map((n) => (
                  <Link
                    key={n.href}
                    href={n.href}
                    className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
                  >
                    {n.label}
                  </Link>
                ))}
              </nav>
            </aside>
            <main className="flex-1 p-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
