import RiskBadge from "./RiskBadge"

const REC_STYLES = {
  Optimal:  {
    bg: "bg-green-500/10",
    border: "border-green-500/30",
    text: "text-green-400",
    glow: "border-glow-green",
  },
  Marginal: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    glow: "border-glow-amber",
  },
  Unsafe:   {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    glow: "border-glow-red",
  },
}

export default function RecommendationCard({ recommendation, riskLevel }) {
  const style = REC_STYLES[recommendation] ?? REC_STYLES.Marginal

  return (
    <div
      className={`
        glass rounded-xl p-6 border ${style.border} ${style.bg} ${style.glow}
        transition-all duration-700 h-full
      `}
    >
      <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500 mb-4">
        Burn Recommendation
      </p>

      <div className="mb-4">
        <span
          className={`text-2xl sm:text-3xl font-black tracking-tight leading-none transition-all duration-700 ${style.text}`}
          style={{ textShadow: "0 0 24px currentColor" }}
        >
          {recommendation?.toUpperCase()}
        </span>
      </div>

      <RiskBadge level={riskLevel} />

      <p className="mt-3 text-[10px] text-zinc-600 tracking-wide uppercase font-medium">
        AI-assisted field decision · human oversight required
      </p>
    </div>
  )
}
