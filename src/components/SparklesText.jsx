import { useEffect, useReducer } from "react"
import { motion } from "motion/react"

const MotionSvg = motion.svg

// Leaf SVG path
const LEAF_PATH = "M10 0C10 0 3 6 3 12C3 16.5 6.5 20 10 20C13.5 20 17 16.5 17 12C17 6 10 0 10 0ZM10 17C7.8 17 6 14.8 6 12C6 9 8.5 5.5 10 3.5C11.5 5.5 14 9 14 12C14 14.8 12.2 17 10 17Z"
// Fire SVG path
const FIRE_PATH = "M10 0C10 0 4 7 4 12C4 15.3 6.7 18 10 18C13.3 18 16 15.3 16 12C16 10.5 15.2 8.8 14 7C14 7 13 9 12 9C12 9 14 4 10 0ZM10 16C8 16 6.5 14.5 6.5 12.5C6.5 10.5 8 8 10 5.5C10 8 12 9 13 8C13.8 9.5 14 10.8 14 12C14 14.5 12 16 10 16Z"

function generateParticle(colors) {
  const isLeaf = Math.random() > 0.45
  return {
    id: `${Math.random()}-${Date.now()}`,
    x: `${Math.random() * 100}%`,
    y: `${Math.random() * 100}%`,
    color: Math.random() > 0.5 ? colors.first : colors.second,
    delay: Math.random() * 2,
    scale: Math.random() * 0.8 + 0.3,
    lifespan: Math.random() * 10 + 5,
    path: isLeaf ? LEAF_PATH : FIRE_PATH,
    viewBox: "0 0 20 20",
  }
}

function createSparkles(colors, sparklesCount) {
  return Array.from({ length: sparklesCount }, () => generateParticle(colors))
}

function sparklesReducer(state, action) {
  switch (action.type) {
    case "reset":
      return createSparkles(action.colors, action.sparklesCount)
    case "tick":
      return state.map((particle) =>
        particle.lifespan <= 0
          ? generateParticle(action.colors)
          : { ...particle, lifespan: particle.lifespan - 0.1 }
      )
    default:
      return state
  }
}

function Particle({ id, x, y, color, delay, scale, path, viewBox }) {
  return (
    <MotionSvg
      key={id}
      className="pointer-events-none absolute z-20"
      initial={{ opacity: 0, left: x, top: y }}
      animate={{
        opacity: [0, 0.9, 0],
        scale: [0, scale, 0],
        rotate: [0, 30, -20],
      }}
      transition={{ duration: 1, repeat: Infinity, delay }}
      width="18"
      height="18"
      viewBox={viewBox}
    >
      <path d={path} fill={color} />
    </MotionSvg>
  )
}

export default function SparklesText({
  text,
  className = "",
  colors = { first: "#f59e0b", second: "#22c55e" },
  sparklesCount = 12,
}) {
  const { first, second } = colors
  const [sparkles, dispatch] = useReducer(
    sparklesReducer,
    { colors: { first, second }, sparklesCount },
    ({ colors: initialColors, sparklesCount: initialCount }) => createSparkles(initialColors, initialCount),
  )

  useEffect(() => {
    const interval = setInterval(() => {
      dispatch({ type: "tick", colors: { first, second } })
    }, 100)

    return () => clearInterval(interval)
  }, [first, second, sparklesCount])

  useEffect(() => {
    dispatch({ type: "reset", colors: { first, second }, sparklesCount })
  }, [first, second, sparklesCount])

  return (
    <div
      className={className}
      style={{
        "--sparkles-first-color": first,
        "--sparkles-second-color": second,
      }}
    >
      <span className="relative inline-block">
        {sparkles.map(s => (
          <Particle key={s.id} {...s} />
        ))}
        <strong>{text}</strong>
      </span>
    </div>
  )
}
