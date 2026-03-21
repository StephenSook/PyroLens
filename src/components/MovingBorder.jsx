import { useRef } from "react"
import {
  motion,
  useAnimationFrame,
  useMotionTemplate,
  useMotionValue,
  useTransform,
} from "motion/react"

const MotionDiv = motion.div

function MovingBorderPath({ duration = 2000, rx, ry, children }) {
  const pathRef = useRef(null)
  const progress = useMotionValue(0)

  useAnimationFrame((time) => {
    const length = pathRef.current?.getTotalLength()
    if (length) {
      const pxPerMillisecond = length / duration
      progress.set((time * pxPerMillisecond) % length)
    }
  })

  const x = useTransform(progress, (val) => pathRef.current?.getPointAtLength(val).x)
  const y = useTransform(progress, (val) => pathRef.current?.getPointAtLength(val).y)
  const transform = useMotionTemplate`translateX(${x}px) translateY(${y}px) translateX(-50%) translateY(-50%)`

  return (
    <>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
        className="absolute h-full w-full"
        width="100%"
        height="100%"
      >
        <rect fill="none" width="100%" height="100%" rx={rx} ry={ry} ref={pathRef} />
      </svg>
      <MotionDiv style={{ position: "absolute", top: 0, left: 0, display: "inline-block", transform }}>
        {children}
      </MotionDiv>
    </>
  )
}

export default function MovingBorder({
  children,
  borderRadius = "9999px",
  duration = 3000,
  borderClassName = "",
  className = "",
  containerClassName = "",
}) {
  return (
    <div
      className={`relative p-[1px] overflow-hidden ${containerClassName}`}
      style={{ borderRadius }}
    >
      <div className="absolute inset-0" style={{ borderRadius: `calc(${borderRadius} * 0.96)` }}>
        <MovingBorderPath duration={duration} rx="30%" ry="30%">
          <div
            className={`h-10 w-10 opacity-[0.8] bg-[radial-gradient(var(--amber-500)_40%,transparent_60%)] ${borderClassName}`}
          />
        </MovingBorderPath>
      </div>
      <div
        className={`relative backdrop-blur-xl flex items-center justify-center w-full h-full antialiased ${className}`}
        style={{ borderRadius: `calc(${borderRadius} * 0.96)` }}
      >
        {children}
      </div>
    </div>
  )
}
