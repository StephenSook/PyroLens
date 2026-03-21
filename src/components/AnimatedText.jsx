import { motion } from "motion/react"

const MotionSpan = motion.span
const MotionDiv = motion.div

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.04, delayChildren: 0.1 },
  },
}

const letterVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", damping: 14, stiffness: 200 },
  },
}

export default function AnimatedText({
  text,
  className = "",
  underlineGradient = "from-amber-500 via-orange-500 to-red-500",
}) {
  const letters = Array.from(text)

  const lineVariants = {
    hidden: { width: "0%", left: "50%" },
    visible: {
      width: "100%",
      left: "0%",
      transition: {
        delay: letters.length * 0.04 + 0.2,
        duration: 0.6,
        ease: "easeOut",
      },
    },
  }

  return (
    <div className="relative inline-block">
      <MotionSpan
        className={`inline-flex overflow-hidden ${className}`}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {letters.map((letter, i) => (
          <MotionSpan key={i} variants={letterVariants}>
            {letter === " " ? "\u00A0" : letter}
          </MotionSpan>
        ))}
      </MotionSpan>
      <MotionDiv
        variants={lineVariants}
        initial="hidden"
        animate="visible"
        className={`absolute -bottom-1 h-[2px] bg-gradient-to-r ${underlineGradient} rounded-full`}
      />
    </div>
  )
}
