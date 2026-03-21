import { useSensorData } from "../hooks/useSensorData"
import Header from "../components/Header"

import SensorCard from "../components/SensorCard"
import BurnScoreCard from "../components/BurnScoreCard"
import RecommendationCard from "../components/RecommendationCard"
import ImpactCard from "../components/ImpactCard"
import FieldDemoVideo from "../components/FieldDemoVideo"
import NetPositiveCard from "../components/NetPositiveCard"
import DataTimestamp from "../components/DataTimestamp"
import StatusPill from "../components/StatusPill"
import ShiningText from "../components/ShiningText"

export default function Dashboard() {
  const { data, error, loading } = useSensorData()
  const { sensor, analysis, project, history, netPositive, site } = data

  return (
    <div className="relative min-h-screen bg-zinc-950 overflow-hidden">

      {/* ── Cinematic video background ── */}
      <div className="fixed inset-0 z-0">
        <video
          src="/Prescribedvideo.mp4"
          autoPlay
          muted
          loop
          playsInline
          className="w-full h-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/50 via-zinc-950/30 to-zinc-950/60" />
        <div
          className="absolute inset-0"
          style={{ background: "radial-gradient(ellipse at center, transparent 60%, rgba(9,9,11,0.4) 100%)" }}
        />
      </div>

      {/* ── App shell ── */}
      <div className="relative z-10 min-h-screen flex flex-col">

        <Header sensor={sensor} project={project} />

        {/* ── Main content ── */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">

          {/* Hero label */}
          <div className="mb-6 sm:mb-8 animate-fade-in">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight">
              <ShiningText
                text="Burn Window Assessment"
                className="text-xl sm:text-2xl font-bold"
              />
            </h2>
            <p className="text-sm text-zinc-500 mt-1">
              Live burn decision context for <span className="text-zinc-400">{site?.label ?? "configured burn site"}</span>
              <span className="hidden sm:inline"> from </span>
              <span className="text-zinc-400 font-mono text-xs"> {sensor.source}</span>
              {project?.pillars?.length > 0 && (
                <span className="hidden sm:inline ml-3">
                  {project.pillars.map(p => (
                    <span key={p} className="inline-flex items-center mx-1 text-[10px] text-zinc-400 uppercase tracking-widest">
                      · {p}
                    </span>
                  ))}
                </span>
              )}
            </p>
          </div>

          {loading && (
            <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-sm text-amber-300 animate-fade-in">
              Syncing live burn window, vegetation, and historical burn context from the backend.
            </div>
          )}

          {/* API error banner */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400 animate-fade-in">
              Backend sync issue: {error} — showing the latest successful dashboard snapshot
            </div>
          )}

          {/* Sensor readings row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="animate-fade-in" style={{ animationDelay: "100ms" }}>
              <SensorCard
                type="temperature"
                value={sensor.temperature_c}
                trend={sensor.trends?.temperature}
                history={history?.temperature}
              />
            </div>
            <div className="animate-fade-in" style={{ animationDelay: "200ms" }}>
              <SensorCard
                type="humidity"
                value={sensor.humidity_pct}
                trend={sensor.trends?.humidity}
                history={history?.humidity}
              />
            </div>
            <div className="animate-fade-in" style={{ animationDelay: "300ms" }}>
              <SensorCard
                type="soil"
                value={sensor.soil_moisture_pct}
                trend={sensor.trends?.soil}
                history={history?.soil}
              />
            </div>
          </div>

          {/* Field Demo Video + Analysis row */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="animate-fade-in" style={{ animationDelay: "350ms" }}>
              <FieldDemoVideo />
            </div>
            <div className="animate-fade-in" style={{ animationDelay: "400ms" }}>
              <BurnScoreCard
                score={analysis.burn_score}
                modelVersion={analysis.model_version}
              />
            </div>
            <div className="animate-fade-in" style={{ animationDelay: "500ms" }}>
              <RecommendationCard
                recommendation={analysis.recommendation}
                riskLevel={analysis.risk_level}
              />
            </div>
            <div className="animate-fade-in" style={{ animationDelay: "600ms" }}>
              <ImpactCard reasoning={analysis.reasoning} />
            </div>
          </div>

          {/* Net Positive Impact section */}
          <div className="animate-fade-in" style={{ animationDelay: "700ms" }}>
            <NetPositiveCard metrics={netPositive} />
          </div>

        </main>

        {/* ── Footer status bar ── */}
        <footer className="glass-dark border-t border-white/[0.05] py-3 px-4 sm:px-6">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <StatusPill status={sensor.status} />
              <DataTimestamp updatedAt={sensor.updated_at} />
            </div>
            <div className="hidden sm:flex items-center gap-2 text-[10px] text-zinc-700 uppercase tracking-widest">
              <span>PyroLens</span>
              <span>·</span>
              <span>{project.track}</span>
            </div>
          </div>
        </footer>

      </div>
    </div>
  )
}
