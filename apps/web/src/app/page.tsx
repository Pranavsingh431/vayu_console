import Link from "next/link";

/**
 * Landing page.
 *
 * One viewport, one action. A judge should know what this is and where to click
 * within five seconds, so there are no feature cards, no statistics, and nothing
 * below the fold to scroll to.
 *
 * The System Status link that used to sit beside the CTA has been removed. It is
 * a diagnostic surface, not a product surface — as a secondary landing action it
 * read like an unfinished feature, and it invited a judge's first click away
 * from the thing being judged. The page itself is still served at /status.
 */

/** The four steps the console actually implements, in the order it runs them. */
const CAPABILITIES = ["Observe", "Evaluate evidence", "Decide", "Explain"];

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-24">
      <div className="w-full max-w-2xl">
        <p className="mb-4 font-mono text-xs tracking-[0.2em] text-[#71717A] uppercase">Delhi</p>

        <h1 className="text-5xl font-semibold tracking-tight text-white sm:text-6xl">
          Vayu Console
        </h1>

        <p className="mt-4 text-xl text-[#A1A1AA] sm:text-2xl">
          Evidence-backed air quality decisions for urban response teams.
        </p>

        <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#71717A]">
          An AQI dashboard tells an officer how bad the air is. Vayu Console shows what evidence
          exists for each possible contributor, what action that evidence justifies, and where the
          evidence runs out.
        </p>

        <ol className="mt-10 flex flex-wrap items-center gap-x-3 gap-y-2">
          {CAPABILITIES.map((step, i) => (
            <li key={step} className="flex items-center gap-3">
              <span className="font-mono text-[11px] tracking-[0.15em] text-[#A1A1AA] uppercase">
                {step}
              </span>
              {i < CAPABILITIES.length - 1 ? (
                <span className="text-[#3F3F46]" aria-hidden>
                  →
                </span>
              ) : null}
            </li>
          ))}
        </ol>

        <div className="mt-10">
          <Link
            href="/console"
            className="inline-flex rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors duration-150 hover:bg-white/90"
          >
            Open Operations Console
          </Link>
        </div>

        {/* Said here rather than discovered in the console: every scenario is a
            reconstruction of a past incident, and that should not be a surprise. */}
        <p className="mt-6 text-xs text-[#52525B]">
          The console replays three reconstructed historical incidents from archived observations.
          It is not a live feed.
        </p>
      </div>
    </main>
  );
}
