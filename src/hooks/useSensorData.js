import { useState, useEffect } from "react"
import { baseMockData, computeBurnScore, scoreToRecommendation, scoreToRisk, generateReasoning } from "../data/mockData"
import { DATA_SOURCE, API_URL, POLL_INTERVAL } from "../data/sensorConfig"

const HISTORY_LENGTH = 20

function simulateTick(prev) {
  const t = parseFloat((prev.sensor.temperature_c + (Math.random() - 0.5) * 1.0).toFixed(1))
  const h = parseFloat(Math.min(100, Math.max(0, prev.sensor.humidity_pct + (Math.random() - 0.5) * 2.0)).toFixed(1))
  const s = parseFloat(Math.min(100, Math.max(0, prev.sensor.soil_moisture_pct + (Math.random() - 0.5) * 1.6)).toFixed(1))

  const score = computeBurnScore(t, h, s)
  const recommendation = scoreToRecommendation(score)
  const risk = scoreToRisk(score)
  const reasoning = generateReasoning(t, h, s)

  return {
    ...prev,
    sensor: {
      ...prev.sensor,
      temperature_c: t,
      humidity_pct: h,
      soil_moisture_pct: s,
      trends: {
        temperature: t > prev.sensor.temperature_c ? "up" : t < prev.sensor.temperature_c ? "down" : "stable",
        humidity: h > prev.sensor.humidity_pct ? "up" : h < prev.sensor.humidity_pct ? "down" : "stable",
        soil: s > prev.sensor.soil_moisture_pct ? "up" : s < prev.sensor.soil_moisture_pct ? "down" : "stable",
      },
      updated_at: new Date().toISOString(),
    },
    analysis: {
      ...prev.analysis,
      burn_score: score,
      recommendation,
      risk_level: risk,
      reasoning,
    },
    history: {
      temperature: [...prev.history.temperature.slice(-(HISTORY_LENGTH - 1)), t],
      humidity: [...prev.history.humidity.slice(-(HISTORY_LENGTH - 1)), h],
      soil: [...prev.history.soil.slice(-(HISTORY_LENGTH - 1)), s],
    },
  }
}

export function useSensorData() {
  const [data, setData] = useState({
    ...baseMockData,
    sensor: {
      ...baseMockData.sensor,
      trends: { temperature: "stable", humidity: "stable", soil: "stable" },
    },
    history: {
      temperature: [baseMockData.sensor.temperature_c],
      humidity: [baseMockData.sensor.humidity_pct],
      soil: [baseMockData.sensor.soil_moisture_pct],
    },
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (DATA_SOURCE === "api") {
      // ── Live mode: poll Tylan's FastAPI backend ──
      let cancelled = false
      const poll = async () => {
        try {
          setLoading(true)
          const res = await fetch(API_URL)
          if (!res.ok) throw new Error(`API ${res.status}`)
          const json = await res.json()
          if (!cancelled) {
            setData(prev => ({
              ...json,
              sensor: {
                ...json.sensor,
                trends: prev.sensor ? {
                  temperature: json.sensor.temperature_c > prev.sensor.temperature_c ? "up" : json.sensor.temperature_c < prev.sensor.temperature_c ? "down" : "stable",
                  humidity: json.sensor.humidity_pct > prev.sensor.humidity_pct ? "up" : json.sensor.humidity_pct < prev.sensor.humidity_pct ? "down" : "stable",
                  soil: json.sensor.soil_moisture_pct > prev.sensor.soil_moisture_pct ? "up" : json.sensor.soil_moisture_pct < prev.sensor.soil_moisture_pct ? "down" : "stable",
                } : { temperature: "stable", humidity: "stable", soil: "stable" },
              },
              history: {
                temperature: [...(prev.history?.temperature ?? []).slice(-(HISTORY_LENGTH - 1)), json.sensor.temperature_c],
                humidity: [...(prev.history?.humidity ?? []).slice(-(HISTORY_LENGTH - 1)), json.sensor.humidity_pct],
                soil: [...(prev.history?.soil ?? []).slice(-(HISTORY_LENGTH - 1)), json.sensor.soil_moisture_pct],
              },
            }))
            setError(null)
          }
        } catch (err) {
          if (!cancelled) setError(err.message)
        } finally {
          if (!cancelled) setLoading(false)
        }
      }
      poll()
      const id = setInterval(poll, POLL_INTERVAL)
      return () => { cancelled = true; clearInterval(id) }
    } else {
      // ── Mock mode: simulated sensor ticks ──
      const id = setInterval(() => {
        setData(prev => simulateTick(prev))
      }, POLL_INTERVAL)
      return () => clearInterval(id)
    }
  }, [])

  return { data, loading, error }
}
