import { useState, useEffect } from "react"

function getRelativeTime(isoString, now = Date.now()) {
  const diff = Math.floor((now - new Date(isoString).getTime()) / 1000)
  if (diff < 5) return "just now"
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function DataTimestamp({ updatedAt }) {
  const [now, setNow] = useState(() => new Date(updatedAt).getTime())
  const label = getRelativeTime(updatedAt, now)

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <span className="text-xs text-zinc-500 font-mono tabular-nums">
      Updated {label}
    </span>
  )
}
