import type { ReactNode } from "react";

interface LegalArticleProps {
  title: string;
  subtitle?: string;
  effectiveDate: string;
  effectiveDateLabel: string;
  children: ReactNode;
}

export function LegalArticle({
  title,
  subtitle,
  effectiveDate,
  effectiveDateLabel,
  children,
}: LegalArticleProps) {
  return (
    <article className="max-w-3xl mx-auto py-10 sm:py-14">
      <header className="mb-10 pb-8 border-b border-gs-quarterly-1">
        <h1 className="font-serif font-bold text-3xl sm:text-4xl leading-tight tracking-tight text-gs-primary mb-3">
          {title}
        </h1>
        {subtitle ? (
          <p className="text-gs-secondary-1 text-base sm:text-lg leading-relaxed mb-4">
            {subtitle}
          </p>
        ) : null}
        <p className="text-xs tracking-wider uppercase text-gs-secondary-2">
          {effectiveDateLabel}: {effectiveDate}
        </p>
      </header>

      <div className="legal-body space-y-6 text-gs-primary text-[15px] leading-7">
        {children}
      </div>
    </article>
  );
}

export function LegalSection({
  heading,
  children,
}: {
  heading: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h2 className="font-serif font-bold text-xl sm:text-2xl text-gs-primary mt-8 mb-3">
        {heading}
      </h2>
      {children}
    </section>
  );
}

export function LegalSubsection({
  heading,
  children,
}: {
  heading: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-base text-gs-primary mt-4">
        {heading}
      </h3>
      {children}
    </div>
  );
}
