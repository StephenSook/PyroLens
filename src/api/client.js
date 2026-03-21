import { API_BASE_URL } from "../data/sensorConfig"

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

function buildUrl(path, query = {}) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  const requestUrl = API_BASE_URL
    ? new URL(normalizedPath, API_BASE_URL)
    : new URL(normalizedPath, window.location.origin)

  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return
    requestUrl.searchParams.set(key, String(value))
  })

  return API_BASE_URL ? requestUrl.toString() : `${normalizedPath}${requestUrl.search}`
}

async function requestJson(path, options = {}) {
  const { query, ...fetchOptions } = options
  const response = await fetch(buildUrl(path, query), {
    headers: {
      Accept: "application/json",
      ...fetchOptions.headers,
    },
    ...fetchOptions,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`

    try {
      const errorPayload = await response.json()
      detail = errorPayload?.detail ?? detail
    } catch {
      // Ignore JSON parse errors and keep the fallback detail.
    }

    throw new ApiError(detail, response.status, detail)
  }

  return response.json()
}

export function getBurnWindow(params) {
  return requestJson("/api/burn-window", { query: params })
}

export function getBurnHistory(params) {
  return requestJson("/api/burns/history", { query: params })
}

export function getNdviSeries(params) {
  return requestJson("/api/satellite/ndvi", { query: params })
}

export function getNetPositiveMetrics(burnId) {
  return requestJson("/api/metrics/net-positive", { query: { burn_id: burnId } })
}

export { ApiError }
