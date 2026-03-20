// ── PyroLens — Central Configuration ──
// Edit this ONE file to switch data sources, update thresholds, or swap the demo video.

// ── Data Source ──
// "mock" = simulated sensor data (for demo)
// "api"  = poll Tylan's FastAPI backend
export const DATA_SOURCE = "mock"
export const API_URL = "/api/sensor"
export const POLL_INTERVAL = 2000 // ms — matches ESP32 delay(2000) in script_0317.ino
export const SENSOR_ID = "esp32-node-01"

// ── Field Demo Video ──
// Drop Pavin's field deployment video in public/ and update this path.
// Set to null to show a placeholder card instead of a player.
export const DEMO_VIDEO_URL = null // e.g. "/field-deploy.mp4"

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
