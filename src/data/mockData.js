// Base mock data — matches team_sensor_schema.json exactly
// Pavin's ESP32: DHT22 (temp + humidity) + soil moisture analog sensor (pin 34, mapped 2000–3300 → 100–0%)

import { NFDRS_THRESHOLDS, NET_POSITIVE_DEFAULTS } from "./sensorConfig"

export const baseMockData = {
  sensor: {
    temperature_c: 18.2,   // within NFDRS safe window (7–24°C)
    humidity_pct: 38.5,    // within NFDRS safe window (25–60%)
    soil_moisture_pct: 28.4, // above 20% threshold
    soil_raw: 2650,
    status: "online",
    updated_at: new Date().toISOString(),
    source: "esp32-node-01",
  },
  analysis: {
    burn_score: 82,
    recommendation: "Optimal",
    risk_level: "Low",
    reasoning: [
      "Temperature within NFDRS prescribed burn window (7–24°C) — supports controlled fire spread",
      "Relative humidity in optimal range (25–60%) — reduces risk of escape while maintaining ignition",
      "Soil moisture above 20% threshold — adequate fuel bed moisture for safe containment",
    ],
    model_version: "pbo-v1.0",
  },
  project: {
    name: "PyroLens",
    track: "Climate Tech",
    pillars: ["Wildfire Prevention", "Ecosystem Restoration", "AI Decision Support"],
  },
}

// ── Net Positive Impact mock data (from research doc) ──
export const netPositiveMetrics = {
  co2_prevented: {
    value: NET_POSITIVE_DEFAULTS.co2_prevented_tons,
    unit: "tons CO₂",
    label: "Emissions Prevented",
    detail: `per ${NET_POSITIVE_DEFAULTS.co2_per_acres} acres of prescribed burn`,
  },
  biodiversity: {
    value: NET_POSITIVE_DEFAULTS.biodiversity_increase_pct,
    unit: "%",
    label: "Biodiversity Increase",
    detail: "native species richness in longleaf pine ecosystems",
  },
  cars_equivalent: {
    value: NET_POSITIVE_DEFAULTS.cars_equivalent,
    unit: "cars",
    label: "Cars Off the Road",
    detail: "equivalent annual emissions reduction",
  },
}

// ── NFDRS-based burn score ──
// Scores each parameter by how well it falls within the safe prescribed burn window.
// A reading inside the NFDRS range scores 100; outside scores 0; borderline scores linearly.
function parameterScore(value, min, max) {
  if (value >= min && value <= max) return 100
  // How far outside the range (linear falloff over 30% of range width)
  const rangeWidth = max - min
  const margin = rangeWidth * 0.3
  if (value < min) return Math.max(0, 100 * (1 - (min - value) / margin))
  return Math.max(0, 100 * (1 - (value - max) / margin))
}

export function computeBurnScore(temp, humidity, soil) {
  const t = NFDRS_THRESHOLDS.temperature
  const h = NFDRS_THRESHOLDS.humidity
  const s = NFDRS_THRESHOLDS.soil

  const tempScore = parameterScore(temp, t.min, t.max)
  const humidityScore = parameterScore(humidity, h.min, h.max)
  const soilScore = parameterScore(soil, s.min, s.max)

  const raw = tempScore * t.weight + humidityScore * h.weight + soilScore * s.weight
  return Math.round(Math.min(100, Math.max(0, raw)))
}

export function scoreToRecommendation(score) {
  if (score >= 71) return "Optimal"
  if (score >= 41) return "Marginal"
  return "Unsafe"
}

export function scoreToRisk(score) {
  if (score >= 71) return "Low"
  if (score >= 41) return "Moderate"
  return "High"
}

// Generate NFDRS reasoning strings from current sensor values
export function generateReasoning(temp, humidity, soil) {
  const t = NFDRS_THRESHOLDS.temperature
  const h = NFDRS_THRESHOLDS.humidity
  const s = NFDRS_THRESHOLDS.soil
  const reasons = []

  if (temp >= t.min && temp <= t.max) {
    reasons.push(`Temperature within NFDRS prescribed burn window (${t.min}–${t.max}°C) — supports controlled fire spread`)
  } else if (temp < t.min) {
    reasons.push(`Temperature below NFDRS minimum (${t.min}°C) — reduced ignition reliability and slow fire progression`)
  } else {
    reasons.push(`Temperature above NFDRS maximum (${t.max}°C) — elevated risk of fire escape and spotting`)
  }

  if (humidity >= h.min && humidity <= h.max) {
    reasons.push(`Relative humidity in optimal range (${h.min}–${h.max}%) — balanced ignition and containment conditions`)
  } else if (humidity < h.min) {
    reasons.push(`Humidity below safe threshold (${h.min}%) — excessive drying increases escape risk`)
  } else {
    reasons.push(`Humidity above optimal range (${h.max}%) — may inhibit ignition and reduce burn effectiveness`)
  }

  if (soil >= s.min) {
    reasons.push(`Soil moisture above ${s.min}% threshold — adequate fuel bed moisture for safe containment`)
  } else {
    reasons.push(`Soil moisture below ${s.min}% — dry subsurface conditions increase deep burn and root damage risk`)
  }

  return reasons
}
