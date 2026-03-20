export default function StatusPill({ status = "offline" }) {
  const isOnline = status === "online"
  const isError = status === "error"

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium tracking-wide">
      <span className="relative flex h-2 w-2">
        {isOnline && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
        )}
        <span
          className={`relative inline-flex rounded-full h-2 w-2 ${
            isOnline ? "bg-green-400" : isError ? "bg-red-400" : "bg-zinc-500"
          }`}
        />
      </span>
      <span className={isOnline ? "text-green-400" : isError ? "text-red-400" : "text-zinc-400"}>
        {isOnline ? "LIVE" : (status ?? "OFFLINE").toUpperCase()}
      </span>
    </span>
  )
}
