import type { Dictionary } from "@/types/analysis";

export default function Footer({ dict }: { dict: Dictionary }) {
  return (
    <footer className="relative z-10 mt-auto py-6 px-5">
      <div className="max-w-shell mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-xs tracking-wider uppercase text-gs-secondary-2">
          &copy; {new Date().getFullYear()} {dict.footer_powered}
        </p>
        <p className="text-xs tracking-wider uppercase text-gs-secondary-2">
          {dict.footer_privacy}
        </p>
      </div>
    </footer>
  );
}
