import { useState } from "react"
import { DEMO_VIDEO_URL } from "../data/sensorConfig"

export default function FieldDemoVideo() {
  const [modalOpen, setModalOpen] = useState(false)
  const hasVideo = !!DEMO_VIDEO_URL

  return (
    <>
      {/* Card */}
      <div
        onClick={() => hasVideo && setModalOpen(true)}
        className={`
          glass rounded-xl p-5 border border-amber-500/20 bg-amber-500/5
          transition-all duration-300 h-full flex flex-col
          ${hasVideo ? "cursor-pointer hover:border-amber-500/40 hover:bg-amber-500/10" : ""}
        `}
      >
        <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500 mb-3">
          Field Sensor Deployment
        </p>

        <div className="flex-1 flex flex-col items-center justify-center py-4">
          {hasVideo ? (
            <>
              <div className="w-16 h-16 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center mb-3 transition-transform hover:scale-110">
                <svg className="w-7 h-7 text-amber-400 ml-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              <p className="text-sm text-zinc-300 font-medium">View Sensor Feed</p>
              <p className="text-[10px] text-zinc-500 mt-1">Click to play field deployment footage</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-full bg-zinc-800/60 border border-white/[0.06] flex items-center justify-center mb-3">
                <svg className="w-7 h-7 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
                </svg>
              </div>
              <p className="text-sm text-zinc-400 font-medium">Video Coming Soon</p>
              <p className="text-[10px] text-zinc-600 mt-1 text-center max-w-[200px]">
                Drop field video in <span className="font-mono text-zinc-500">public/</span> and update <span className="font-mono text-zinc-500">sensorConfig.js</span>
              </p>
            </>
          )}
        </div>

      </div>

      {/* Modal */}
      {modalOpen && hasVideo && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setModalOpen(false)}
        >
          <div
            className="relative w-full max-w-4xl mx-4"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setModalOpen(false)}
              className="absolute -top-10 right-0 text-zinc-400 hover:text-white text-sm font-medium tracking-wide uppercase transition-colors"
            >
              Close ✕
            </button>
            <video
              src={DEMO_VIDEO_URL}
              controls
              autoPlay
              className="w-full rounded-xl border border-white/10 shadow-2xl"
            />
          </div>
        </div>
      )}
    </>
  )
}
