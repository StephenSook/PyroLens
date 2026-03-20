const RISK_STYLES = {
  Low:      "bg-green-500/15 text-green-400 border-green-500/30",
  Moderate: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  High:     "bg-red-500/15 text-red-400 border-red-500/30",
}

export default function RiskBadge({ level }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-widest border ${
        RISK_STYLES[level] ?? RISK_STYLES.Moderate
      }`}
    >
      {level?.toUpperCase()} RISK
    </span>
  )
}
