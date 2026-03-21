import { motion } from "motion/react"

const MotionSpan = motion.span

export default function ShiningText({ text, className = "" }) {
  return (
    <MotionSpan
      className={`bg-[linear-gradient(110deg,#525252,35%,#fbbf24,50%,#525252,75%,#525252)] bg-[length:200%_100%] bg-clip-text text-transparent ${className}`}
      initial={{ backgroundPosition: "200% 0" }}
      animate={{ backgroundPosition: "-200% 0" }}
      transition={{
        repeat: Infinity,
        duration: 3,
        ease: "linear",
      }}
    >
      {text}
    </MotionSpan>
  )
}
