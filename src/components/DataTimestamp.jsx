import { useState, useEffect } from "react"

function getRelativeTime(isoString) {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 5) return "just now"
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function DataTimestamp({ updatedAt }) {
  const [label, setLabel] = useState(getRelativeTime(updatedAt))

  useEffect(() => {
    setLabel(getRelativeTime(updatedAt))
    const id = setInterval(() => setLabel(getRelativeTime(updatedAt)), 1000)
    return () => clearInterval(id)
  }, [updatedAt])

  return (
    <span className="text-xs text-zinc-500 font-mono tabular-nums">
      Updated {label}
    </span>
  )
}
