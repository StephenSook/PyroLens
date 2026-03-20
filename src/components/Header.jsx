import StatusPill from "./StatusPill"
import AnimatedText from "./AnimatedText"
import ShiningText from "./ShiningText"
import MovingBorder from "./MovingBorder"

export default function Header({ sensor, project }) {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-zinc-950/30 border-b border-white/[0.05]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">

        {/* Wordmark */}
        <div>
          <AnimatedText
            text="PyroLens"
            className="text-lg sm:text-xl font-semibold text-zinc-100 tracking-tight leading-none"
            underlineGradient="from-amber-500 via-orange-500 to-red-500"
          />
          <div className="mt-1.5">
            <ShiningText
              text="Burn Window Decision Support"
              className="text-xs sm:text-sm tracking-widest uppercase font-medium"
            />
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {project?.track && (
            <MovingBorder
              borderRadius="9999px"
              duration={3000}
              className="bg-amber-500/10 border border-amber-500/15 px-2.5 py-1"
            >
              <span className="text-[10px] font-semibold tracking-widest uppercase text-amber-400 whitespace-nowrap">
                {project.track}
              </span>
            </MovingBorder>
          )}
          <StatusPill status={sensor?.status ?? "offline"} />
        </div>

      </div>
    </header>
  )
}
