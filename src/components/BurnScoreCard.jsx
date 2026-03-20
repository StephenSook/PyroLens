import { useAnimatedValue } from "../hooks/useAnimatedValue"

function getScoreStyle(score) {
  if (score >= 71) return { color: "#22c55e", glow: "border-glow-green", label: "Optimal" }
  if (score >= 41) return { color: "#f97316", glow: "border-glow-amber", label: "Marginal" }
  return { color: "#ef4444", glow: "border-glow-red", label: "Unsafe" }
}

function ScoreArc({ score, color }) {
  const size = 140
  const stroke = 10
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const arcLength = circumference * 0.75
  const dashOffset = arcLength - (arcLength * Math.min(100, Math.max(0, score))) / 100

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="rotate-[135deg]"
      aria-hidden="true"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={stroke}
        strokeDasharray={`${arcLength} ${circumference}`}
        strokeLinecap="round"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={`${arcLength} ${circumference}`}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.8s ease" }}
      />
    </svg>
  )
}

export default function BurnScoreCard({ score, modelVersion }) {
  const { color, glow } = getScoreStyle(score)
  const animatedScore = useAnimatedValue(score, 800)

  return (
    <div className={`glass rounded-xl p-6 border border-white/[0.07] ${glow} transition-all duration-700 h-full`}>
      <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500 mb-4">
        Burn Readiness Score
      </p>

      <div className="flex flex-col items-center">
        <div className="relative">
          <ScoreArc score={score} color={color} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-4xl font-bold tabular-nums leading-none transition-colors duration-700"
              style={{ color, textShadow: `0 0 20px ${color}55` }}
            >
              {Math.round(animatedScore)}
            </span>
            <span className="text-[10px] text-zinc-500 mt-1">/ 100</span>
          </div>
        </div>
      </div>

      {modelVersion && (
        <div className="mt-4 flex justify-center">
          <span className="text-[9px] text-zinc-600 font-mono tracking-widest uppercase border border-white/[0.06] px-2 py-0.5 rounded-full">
            {modelVersion}
          </span>
        </div>
      )}
    </div>
  )
}
