import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "AEO Visibility Diagnostic",
  description: "Analyze how visible your website is in AI search engines",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
