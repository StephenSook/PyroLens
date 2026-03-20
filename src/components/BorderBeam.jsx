export default function BorderBeam({
  colorFrom = "#ffaa40",
  colorTo = "#9c40ff",
  duration = 8,
  delay = 0,
}) {
  return (
    <>
      <div
        className="absolute inset-0 rounded-xl z-0 opacity-70"
        style={{
          padding: "1.5px",
          background: `conic-gradient(from 0deg, transparent 60%, ${colorFrom}, ${colorTo}, transparent 100%)`,
          WebkitMask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
          WebkitMaskComposite: "xor",
          maskComposite: "exclude",
          animation: `spin ${duration}s linear infinite`,
          animationDelay: `${delay}s`,
        }}
      />
      <style>{`
        @keyframes spin {
          to { rotate: 360deg; }
        }
      `}</style>
    </>
  )
}
