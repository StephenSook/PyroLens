import { useState, useEffect, useRef } from "react"

export function useAnimatedValue(target, duration = 500) {
  const [value, setValue] = useState(target)
  const prev = useRef(target)
  const raf = useRef(0)

  useEffect(() => {
    const from = prev.current
    prev.current = target
    if (from === target) return

    const start = performance.now()

    function tick(now) {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - (1 - t) ** 3 // ease-out cubic
      setValue(from + (target - from) * eased)
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }

    cancelAnimationFrame(raf.current)
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])

  return value
}
