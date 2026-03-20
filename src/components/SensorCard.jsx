import { useAnimatedValue } from "../hooks/useAnimatedValue"
import { NFDRS_THRESHOLDS } from "../data/sensorConfig"

function getNfdrsStatus(type, value) {
  const t = NFDRS_THRESHOLDS[type]
  if (!t) return null
  const rangeWidth = t.max - t.min
  const margin = rangeWidth * 0.15
  if (value >= t.min && value <= t.max) return "safe"
  if (value >= t.min - margin && value <= t.max + margin) return "borderline"
  return "unsafe"
}

function ThresholdIndicator({ type, value }) {
  const status = getNfdrsStatus(type, value)
  const t = NFDRS_THRESHOLDS[type]
  if (!status || !t) return null

  const config = {
    safe:       { icon: "✓", color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30", label: "In range" },
    borderline: { icon: "!", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/30", label: "Borderline" },
    unsafe:     { icon: "✕", color: "text-red-400",   bg: "bg-red-500/10",   border: "border-red-500/30",   label: "Out of range" },
  }[status]

  return (
    <div className="mt-2 flex items-center justify-between">
      <span className="text-xs text-zinc-500">
        Safe: {t.min}–{t.max}{t.unit}
      </span>
      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-1.5 py-0.5 rounded-full border ${config.bg} ${config.border} ${config.color}`}>
        {config.icon} {config.label}
      </span>
    </div>
  )
}

function TempIcon() {
  return (
    <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m0 0a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0-9a1.5 1.5 0 0 0-1.5 1.5v7.59a3 3 0 1 0 3 0V4.5A1.5 1.5 0 0 0 12 3Z" />
    </svg>
  )
}
function DropIcon() {
  return (
    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21.5c-3.6 0-6.5-2.9-6.5-6.5 0-4.5 6.5-12.5 6.5-12.5s6.5 8 6.5 12.5c0 3.6-2.9 6.5-6.5 6.5Z" />
    </svg>
  )
}
function SoilIcon() {
  return (
    <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21c-4-2-7-5.5-7-9.5C5 7 8.5 3 12 3c1.5 0 3 .5 4 1.5-1 1-2 3-2 5 0 3 2 5 4 6-1 3-3.5 5-6 5.5Z" />
    </svg>
  )
}

const CARD_CONFIG = {
  temperature: {
    IconComponent: TempIcon,
    label: "Temperature",
    unit: "°C",
    borderClass: "border-amber-500/20",
    valueClass: "text-amber-400",
    bgClass: "bg-amber-500/5",
    sparkColor: "#f59e0b",
    subLabel: "Air temperature",
  },
  humidity: {
    IconComponent: DropIcon,
    label: "Humidity",
    unit: "%",
    borderClass: "border-blue-500/20",
    valueClass: "text-blue-400",
    bgClass: "bg-blue-500/5",
    sparkColor: "#3b82f6",
    subLabel: "Relative humidity",
  },
  soil: {
    IconComponent: SoilIcon,
    label: "Soil Moisture",
    unit: "%",
    borderClass: "border-green-500/20",
    valueClass: "text-green-400",
    bgClass: "bg-green-500/5",
    sparkColor: "#22c55e",
    subLabel: "Volumetric water content",
  },
}

function Sparkline({ data, color, height = 28 }) {
  if (!data || data.length < 2) return <div style={{ height }} />

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 100

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - 2 - ((v - min) / range) * (height - 4)
    return `${x},${y}`
  }).join(" ")

  return (
    <svg
      viewBox={`0 0 ${w} ${height}`}
      preserveAspectRatio="none"
      className="w-full"
      style={{ height }}
      aria-hidden="true"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.4"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}

function TrendArrow({ direction }) {
  if (!direction || direction === "stable") return null
  return (
    <span className="text-[10px] text-zinc-500 mb-0.5 ml-0.5">
      {direction === "up" ? "▲" : "▼"}
    </span>
  )
}

export default function SensorCard({ type, value, trend, history }) {
  const config = CARD_CONFIG[type]
  if (!config) return null

  const animatedValue = useAnimatedValue(typeof value === "number" ? value : 0, 600)
  const display = typeof value === "number" ? animatedValue.toFixed(1) : "--"

  return (
    <div
      className={`
        glass rounded-xl p-4 sm:p-5 border ${config.borderClass} ${config.bgClass}
        transition-all duration-700 h-full
      `}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500">
            {config.subLabel}
          </p>
          <p className="text-base font-medium text-zinc-300 mt-0.5">{config.label}</p>
        </div>
        <config.IconComponent />
      </div>

      <div className="flex items-end gap-1 mt-4">
        <span className={`text-3xl sm:text-4xl font-bold tabular-nums leading-none ${config.valueClass}`}>
          {display}
        </span>
        <span className="text-sm text-zinc-500 mb-0.5">{config.unit}</span>
        <TrendArrow direction={trend} />
      </div>

      <div className="mt-3 -mx-1">
        <Sparkline data={history} color={config.sparkColor} />
      </div>

      <ThresholdIndicator type={type} value={value} />
    </div>
  )
}
