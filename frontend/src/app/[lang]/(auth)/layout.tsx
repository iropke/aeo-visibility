/**
 * (auth) 라우트 그룹 레이아웃 — signup / login / verify / onboarding 공용.
 * 미니멀한 중앙 정렬 카드 형태.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex-1 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">{children}</div>
    </main>
  );
}
