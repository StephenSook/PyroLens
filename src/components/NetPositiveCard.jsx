import SparklesText from "./SparklesText"
import BorderBeam from "./BorderBeam"

const METRIC_STYLES = {
  co2_prevented: {
    color: "text-emerald-400",
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/5",
    beamFrom: "#34d399",
    beamTo: "#059669",
    beamDelay: 0,
  },
  biodiversity: {
    color: "text-blue-400",
    border: "border-blue-500/20",
    bg: "bg-blue-500/5",
    beamFrom: "#60a5fa",
    beamTo: "#2563eb",
    beamDelay: 3,
  },
  cars_equivalent: {
    color: "text-purple-400",
    border: "border-purple-500/20",
    bg: "bg-purple-500/5",
    beamFrom: "#c084fc",
    beamTo: "#7c3aed",
    beamDelay: 6,
  },
}

function MetricItem({ metricKey, data }) {
  const style = METRIC_STYLES[metricKey]
  if (!style || !data) return null

  return (
    <div className={`relative glass rounded-xl p-4 border ${style.border} ${style.bg} transition-all duration-300 overflow-hidden`}>
      <BorderBeam
        size={150}
        duration={10}
        colorFrom={style.beamFrom}
        colorTo={style.beamTo}
        delay={style.beamDelay}
        borderWidth={1.5}
      />
      <div className="mb-2">
        <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500">
          {data.label}
        </p>
      </div>
      <div className="flex items-end gap-1.5">
        <span className={`text-2xl sm:text-3xl font-bold tabular-nums leading-none ${style.color}`}>
          {data.value.toLocaleString()}
        </span>
        <span className="text-sm text-zinc-500 mb-0.5">{data.unit}</span>
      </div>
      <p className="text-xs text-zinc-500 mt-2 leading-snug">{data.detail}</p>
    </div>
  )
}

export default function NetPositiveCard({ metrics }) {
  return (
    <div>
      <div className="mb-5">
        <SparklesText
          text="Net Positive Impact"
          className="text-lg sm:text-xl font-bold text-zinc-100 tracking-tight"
          colors={{ first: "#f59e0b", second: "#22c55e" }}
          sparklesCount={10}
        />
        <SparklesText
          text="Prescribed burns prevent catastrophic wildfire — here's the projected environmental return"
          className="text-sm text-zinc-400 mt-1.5 leading-relaxed"
          colors={{ first: "#f59e0b", second: "#22c55e" }}
          sparklesCount={6}
        />
      </div>
      {metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          <MetricItem metricKey="co2_prevented" data={metrics.co2_prevented} />
          <MetricItem metricKey="biodiversity" data={metrics.biodiversity} />
          <MetricItem metricKey="cars_equivalent" data={metrics.cars_equivalent} />
        </div>
      ) : (
        <div className="glass rounded-xl p-5 border border-white/[0.07]">
          <p className="text-sm text-zinc-300 leading-relaxed">
            Net positive impact metrics will appear once PyroLens can match this dashboard location to a historical burn with available backend metrics.
          </p>
        </div>
      )}
    </div>
  )
}
