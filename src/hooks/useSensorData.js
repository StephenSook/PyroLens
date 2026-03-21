import { useState, useEffect } from "react"
import {
  baseMockData,
  computeBurnScore,
  scoreToRecommendation,
  scoreToRisk,
  generateReasoning,
} from "../data/mockData"
import {
  DATA_SOURCE,
  POLL_INTERVAL,
  DASHBOARD_LOCATION,
  NDVI_LOOKBACK_DAYS,
  BURN_HISTORY_LOOKBACK_DAYS,
  PROJECT_METADATA,
} from "../data/sensorConfig"
import { ApiError, getBurnHistory, getBurnWindow, getNdviSeries, getNetPositiveMetrics } from "../api/client"

const HISTORY_LENGTH = 20
const VEHICLE_EMISSIONS_TONS = 4.6

function toIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

function subtractDays(date, days) {
  const nextDate = new Date(date)
  nextDate.setDate(nextDate.getDate() - days)
  return nextDate
}

function roundTo(value, digits = 1) {
  if (typeof value !== "number" || Number.isNaN(value)) return null
  return Number(value.toFixed(digits))
}

function buildInitialData(sourceMode = DATA_SOURCE) {
  return {
    ...baseMockData,
    sensor: {
      ...baseMockData.sensor,
      source: sourceMode === "mock" ? baseMockData.sensor.source : "backend-sync",
      trends: { temperature: "stable", humidity: "stable", soil: "stable" },
    },
    analysis: {
      ...baseMockData.analysis,
      reasoning: sourceMode === "mock" ? baseMockData.analysis.reasoning : [],
      model_version: sourceMode === "mock" ? baseMockData.analysis.model_version : "backend-ml",
      next_optimal_window: null,
      ndvi: null,
      matched_burn_id: null,
    },
    project: PROJECT_METADATA,
    history: {
      temperature: [baseMockData.sensor.temperature_c],
      humidity: [baseMockData.sensor.humidity_pct],
      soil: [baseMockData.sensor.soil_moisture_pct],
    },
    netPositive: null,
    site: {
      label: DASHBOARD_LOCATION.label,
      coordinates: { lat: DASHBOARD_LOCATION.lat, lon: DASHBOARD_LOCATION.lon },
      latestBurn: null,
      burnHistory: [],
      ndviSeries: [],
    },
  }
}

function buildHistorySeries(previousSeries = [], nextValue, fallbackValue) {
  const resolvedValue = typeof nextValue === "number" ? nextValue : fallbackValue
  return [...previousSeries.slice(-(HISTORY_LENGTH - 1)), resolvedValue]
}

function getTrend(nextValue, previousValue) {
  if (typeof nextValue !== "number" || typeof previousValue !== "number") return "stable"
  if (nextValue > previousValue) return "up"
  if (nextValue < previousValue) return "down"
  return "stable"
}

function getFeatureId(feature) {
  return feature?.properties?.id ?? null
}

function selectRelevantBurn(features, matchedBurnId) {
  if (!Array.isArray(features) || features.length === 0) return null
  if (matchedBurnId !== null && matchedBurnId !== undefined) {
    const exactMatch = features.find(feature => getFeatureId(feature) === matchedBurnId)
    if (exactMatch) return exactMatch
  }
  return features[0]
}

function formatBurnSummary(feature) {
  if (!feature?.properties) return null

  const { county, burn_date: burnDate, acreage, objective, outcome } = feature.properties
  const acreageLabel = typeof acreage === "number" ? `${Math.round(acreage).toLocaleString()} acres` : "documented acreage"
  return {
    county: county ?? "Unknown county",
    burnDate: burnDate ?? null,
    acreageLabel,
    objective: objective ?? "Prescribed burn activity",
    outcome: outcome ?? "Recorded outcome unavailable",
  }
}

function summarizeNdvi(series) {
  if (!Array.isArray(series) || series.length === 0) return null

  const firstPoint = series[0]
  const latestPoint = series[series.length - 1]
  const delta = latestPoint.ndvi - firstPoint.ndvi

  return {
    latest: roundTo(latestPoint.ndvi, 2),
    delta: roundTo(delta, 2),
    trend: delta > 0.02 ? "improving" : delta < -0.02 ? "softening" : "steady",
  }
}

function buildNetPositive(metrics, matchedBurn) {
  if (!metrics) return null

  const burnSummary = formatBurnSummary(matchedBurn)
  const carsEquivalent = Math.max(1, Math.round(metrics.co2_prevented / VEHICLE_EMISSIONS_TONS))
  const biodiversityPercent = Math.round(metrics.biodiversity_gain_index * 100)
  const burnLabel = burnSummary?.burnDate
    ? `for the ${burnSummary.county} burn on ${burnSummary.burnDate}`
    : `for burn #${metrics.burn_id}`

  return {
    co2_prevented: {
      value: Math.round(metrics.co2_prevented),
      unit: "tons CO2",
      label: "Emissions Prevented",
      detail: `Avoided wildfire emissions ${burnLabel}`,
    },
    biodiversity: {
      value: biodiversityPercent,
      unit: "%",
      label: "Biodiversity Gain",
      detail: `${metrics.fuel_load_reduction_pct.toFixed(1)}% fuel-load reduction with vegetation recovery tracking`,
    },
    cars_equivalent: {
      value: carsEquivalent,
      unit: "cars",
      label: "Cars Off the Road",
      detail: `${Math.round(metrics.wildfire_baseline_emissions).toLocaleString()} tons wildfire baseline emissions equivalent`,
    },
  }
}

function buildReasoning({ burnWindow, ndviSeries, matchedBurn, metrics }) {
  const reasons = generateReasoning(
    burnWindow.conditions.temperature,
    burnWindow.conditions.humidity,
    burnWindow.conditions.soil_moisture,
  )

  if (burnWindow.next_optimal_window) {
    reasons.push(`Forecast-aligned next optimal burn window begins ${burnWindow.next_optimal_window}`)
  } else {
    reasons.push("No better near-term burn window was identified in the current forecast horizon")
  }

  const ndviSummary = summarizeNdvi(ndviSeries)
  if (ndviSummary) {
    reasons.push(`Sentinel NDVI is ${ndviSummary.latest} and ${ndviSummary.trend} over the recent observation window`)
  }

  const burnSummary = formatBurnSummary(matchedBurn)
  if (burnSummary) {
    reasons.push(
      `${burnSummary.county} history shows a burn on ${burnSummary.burnDate} covering ${burnSummary.acreageLabel} for ${burnSummary.objective.toLowerCase()}`,
    )
  }

  if (metrics) {
    reasons.push(
      `Net positive estimate shows ${Math.round(metrics.co2_prevented).toLocaleString()} tons of avoided CO2 and ${metrics.fuel_load_reduction_pct.toFixed(1)}% fuel-load reduction`,
    )
  }

  return reasons.slice(0, 6)
}

function buildApiSensorSource(burnWindow) {
  if (burnWindow.sensor_device_id) return burnWindow.sensor_device_id
  return burnWindow.sensor_data === "live" ? "backend-live-sensor" : "backend-weather-defaults"
}

function formatErrors(errors) {
  if (errors.length === 0) return null
  return errors.join(" | ")
}

function getErrorDetail(error) {
  if (error instanceof ApiError) return error.detail
  if (error instanceof Error) return error.message
  return "Unexpected backend error"
}

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
  const [data, setData] = useState(() => buildInitialData())
  const [loading, setLoading] = useState(DATA_SOURCE === "api")
  const [error, setError] = useState(null)

  useEffect(() => {
    if (DATA_SOURCE === "api") {
      let cancelled = false

      const poll = async () => {
        const pollStartedAt = new Date()
        const historyStartDate = subtractDays(pollStartedAt, BURN_HISTORY_LOOKBACK_DAYS)
        const ndviStartDate = subtractDays(pollStartedAt, NDVI_LOOKBACK_DAYS)
        const partialErrors = []

        try {
          setLoading(true)
          const [burnWindowResult, burnHistoryResult, ndviResult] = await Promise.allSettled([
            getBurnWindow({
              lat: DASHBOARD_LOCATION.lat,
              lon: DASHBOARD_LOCATION.lon,
              date: toIsoDate(pollStartedAt),
            }),
            getBurnHistory({
              county: DASHBOARD_LOCATION.county || undefined,
              from_date: toIsoDate(historyStartDate),
            }),
            getNdviSeries({
              lat: DASHBOARD_LOCATION.lat,
              lon: DASHBOARD_LOCATION.lon,
              start_date: toIsoDate(ndviStartDate),
              end_date: toIsoDate(pollStartedAt),
            }),
          ])

          if (burnWindowResult.status === "rejected") {
            throw burnWindowResult.reason
          }

          const burnWindow = burnWindowResult.value
          const burnHistoryFeatures = burnHistoryResult.status === "fulfilled"
            ? burnHistoryResult.value?.features ?? []
            : []
          const ndviSeries = ndviResult.status === "fulfilled"
            ? ndviResult.value?.series ?? []
            : []

          if (burnHistoryResult.status === "rejected") {
            partialErrors.push(`Burn history: ${getErrorDetail(burnHistoryResult.reason)}`)
          }

          if (ndviResult.status === "rejected") {
            partialErrors.push(`NDVI: ${getErrorDetail(ndviResult.reason)}`)
          }

          const matchedBurn = selectRelevantBurn(burnHistoryFeatures, burnWindow.matched_burn_id)
          const matchedBurnId = getFeatureId(matchedBurn)

          let netPositiveMetrics = null
          if (matchedBurnId) {
            try {
              netPositiveMetrics = await getNetPositiveMetrics(matchedBurnId)
            } catch (metricsError) {
              if (!(metricsError instanceof ApiError && metricsError.status === 404)) {
                partialErrors.push(`Net positive metrics: ${getErrorDetail(metricsError)}`)
              }
            }
          }

          if (cancelled) return

          setData(prev => {
            const temperature = roundTo(burnWindow.conditions.temperature, 1) ?? prev.sensor.temperature_c
            const humidity = roundTo(burnWindow.conditions.humidity, 1) ?? prev.sensor.humidity_pct
            const soilMoisture = roundTo(burnWindow.conditions.soil_moisture, 1) ?? prev.sensor.soil_moisture_pct

            return {
              ...prev,
              project: PROJECT_METADATA,
              sensor: {
                ...prev.sensor,
                temperature_c: temperature,
                humidity_pct: humidity,
                soil_moisture_pct: soilMoisture,
                status: burnWindow.sensor_data === "live" ? "online" : "offline",
                updated_at: burnWindow.sensor_timestamp ?? pollStartedAt.toISOString(),
                source: buildApiSensorSource(burnWindow),
                trends: {
                  temperature: getTrend(temperature, prev.sensor.temperature_c),
                  humidity: getTrend(humidity, prev.sensor.humidity_pct),
                  soil: getTrend(soilMoisture, prev.sensor.soil_moisture_pct),
                },
              },
              analysis: {
                burn_score: burnWindow.burn_score,
                recommendation: burnWindow.recommendation,
                risk_level: scoreToRisk(burnWindow.burn_score),
                reasoning: buildReasoning({
                  burnWindow,
                  ndviSeries,
                  matchedBurn,
                  metrics: netPositiveMetrics,
                }),
                model_version: burnWindow.model_source === "ml" ? "backend-ml" : burnWindow.model_source,
                next_optimal_window: burnWindow.next_optimal_window,
                ndvi: burnWindow.ndvi,
                matched_burn_id: burnWindow.matched_burn_id ?? matchedBurnId ?? null,
              },
              history: {
                temperature: buildHistorySeries(prev.history?.temperature, temperature, prev.sensor.temperature_c),
                humidity: buildHistorySeries(prev.history?.humidity, humidity, prev.sensor.humidity_pct),
                soil: buildHistorySeries(prev.history?.soil, soilMoisture, prev.sensor.soil_moisture_pct),
              },
              netPositive: buildNetPositive(netPositiveMetrics, matchedBurn),
              site: {
                label: DASHBOARD_LOCATION.label,
                coordinates: { lat: DASHBOARD_LOCATION.lat, lon: DASHBOARD_LOCATION.lon },
                latestBurn: matchedBurn,
                burnHistory: burnHistoryFeatures,
                ndviSeries,
              },
            }
          })

          setError(formatErrors(partialErrors))
        } catch (err) {
          if (!cancelled) {
            setError(`Burn window: ${getErrorDetail(err)}`)
          }
        } finally {
          if (!cancelled) setLoading(false)
        }
      }

      poll()
      const id = setInterval(poll, POLL_INTERVAL)
      return () => {
        cancelled = true
        clearInterval(id)
      }
    } else {
      const id = setInterval(() => {
        setData(prev => simulateTick(prev))
      }, POLL_INTERVAL)
      return () => clearInterval(id)
    }
  }, [])

  return { data, loading, error }
}
