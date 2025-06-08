import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./app.css";
import AmplifyProvider from "./amplify-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Wine CRM Developer Dashboard",
  description: "Wine Import CRM API Testing Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AmplifyProvider>
          {children}
        </AmplifyProvider>
      </body>
    </html>
  );
}