export default function ImpactCard({ reasoning }) {
  if (!reasoning?.length) return null

  return (
    <div className="glass rounded-xl p-5 border border-white/[0.07] h-full flex flex-col">
      <p className="text-xs font-semibold tracking-widest uppercase text-zinc-500 mb-4">
        Why this score?
      </p>

      <ul className="space-y-3 flex-1">
        {reasoning.map((reason, i) => (
          <li key={i} className="flex items-start gap-3">
            <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-500/60 flex-shrink-0" />
            <span className="text-sm text-zinc-300 leading-snug">{reason}</span>
          </li>
        ))}
      </ul>

    </div>
  )
}
