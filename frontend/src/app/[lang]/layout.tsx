import type { Metadata } from "next";
import { locales, type Locale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/getDictionary";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

export async function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  return {
    title: dict.site_title,
    description: dict.site_description,
  };
}

export default async function LangLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  return (
    <html lang={lang} data-lang={lang}>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        {lang === "ko" && (
          <link
            href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
            rel="stylesheet"
          />
        )}
      </head>
      <body className="page-bg min-h-screen flex flex-col">
        <Header lang={lang as Locale} dict={dict} />
        <main className="flex-1 w-full max-w-shell mx-auto px-4 sm:px-5 pt-8 pb-20">
          {children}
        </main>
        <Footer dict={dict} />
      </body>
    </html>
  );
}
