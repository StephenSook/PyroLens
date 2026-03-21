// ── PyroLens — Central Configuration ──
// Use Vite env vars for backend connectivity and site selection.

function getEnvNumber(key, fallback) {
  const rawValue = import.meta.env[key]
  if (rawValue === undefined || rawValue === "") return fallback

  const parsedValue = Number(rawValue)
  return Number.isFinite(parsedValue) ? parsedValue : fallback
}

function getEnvString(key, fallback) {
  const rawValue = import.meta.env[key]
  return rawValue === undefined || rawValue === "" ? fallback : rawValue
}

// ── Data Source ──
// "mock" = simulated sensor data (for demo)
// "api"  = poll the FastAPI backend and compose dashboard data from multiple endpoints
export const DATA_SOURCE = getEnvString("VITE_DATA_SOURCE", "api")
export const API_BASE_URL = getEnvString("VITE_API_BASE_URL", "").replace(/\/$/, "")
export const POLL_INTERVAL = getEnvNumber("VITE_POLL_INTERVAL_MS", 30000)

export const DASHBOARD_LOCATION = {
  label: getEnvString("VITE_SITE_LABEL", "Georgia Pilot Burn Site"),
  lat: getEnvNumber("VITE_SITE_LAT", 33.749),
  lon: getEnvNumber("VITE_SITE_LON", -84.388),
  county: getEnvString("VITE_SITE_COUNTY", ""),
}

export const NDVI_LOOKBACK_DAYS = getEnvNumber("VITE_NDVI_LOOKBACK_DAYS", 90)
export const BURN_HISTORY_LOOKBACK_DAYS = getEnvNumber("VITE_BURN_HISTORY_LOOKBACK_DAYS", 3650)
export const ACTIVE_FIRE_DAY_RANGE = getEnvNumber("VITE_ACTIVE_FIRE_DAY_RANGE", 3)
export const ACTIVE_FIRE_BBOX_DELTA = getEnvNumber("VITE_ACTIVE_FIRE_BBOX_DELTA", 0.5)

// ── Field Demo Video ──
// Drop Pavin's field deployment video in public/ and update this path.
// Set to null to show a placeholder card instead of a player.
export const DEMO_VIDEO_URL = "/demo-video.mp4"

// ── NFDRS Burn Window Thresholds ──
// Source: NFDRS criteria from PyroLens Research doc
// Each parameter has a safe range for prescribed burning.
export const NFDRS_THRESHOLDS = {
  temperature: {
    label: "Temperature",
    unit: "°C",
    min: 7,   // ~45°F
    max: 24,  // ~75°F
    weight: 0.30,
  },
  humidity: {
    label: "Humidity",
    unit: "%",
    min: 25,
    max: 60,
    weight: 0.40,
  },
  soil: {
    label: "Soil Moisture",
    unit: "%",
    min: 20,
    max: 100, // wetter is safer; below 20% is too dry
    weight: 0.30,
  },
}

// ── Pavin's ESP32 Calibration (from script_0317.ino) ──
export const SOIL_CALIBRATION = {
  rawMin: 2000,  // dry / air
  rawMax: 3300,  // wet / water
  pctMin: 0,
  pctMax: 100,
}

// ── Net Positive Impact Defaults (from research doc) ──
export const NET_POSITIVE_DEFAULTS = {
  co2_prevented_tons: 6000,
  co2_per_acres: 100,
  biodiversity_increase_pct: 87,
  cars_equivalent: 1300,
}

export const PROJECT_METADATA = {
  name: "PyroLens",
  track: "Climate Tech",
  pillars: ["Wildfire Prevention", "Ecosystem Restoration", "AI Decision Support"],
}
