import Link from "next/link";

/**
 * Landing page.
 *
 * Deliberately just the product's name and what it is. Phase 0 is foundation
 * work; marketing copy and product surfaces come with the features.
 */
export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-24">
      <div className="w-full max-w-2xl">
        <p className="mb-4 font-mono text-xs tracking-[0.2em] text-muted-foreground uppercase">
          Delhi
        </p>
        <h1 className="text-5xl font-semibold tracking-tight text-foreground sm:text-6xl">
          Vayu Console
        </h1>
        <p className="mt-4 text-xl text-muted-foreground sm:text-2xl">
          Urban Air Quality Decision Intelligence
        </p>
        <div className="mt-10 flex items-center gap-5">
          <Link
            href="/console"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            Open Operations Console
          </Link>
          <Link
            href="/status"
            className="text-sm font-medium text-muted-foreground underline-offset-4 hover:underline"
          >
            System status
          </Link>
        </div>
      </div>
    </main>
  );
}
