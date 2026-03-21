# API Examples

These examples assume the backend is running at `http://localhost:8000`.

## Burn Window

```bash
curl "http://localhost:8000/api/burn-window?lat=33.7490&lon=-84.3880"
```

## Sensors

```bash
curl -X POST "http://localhost:8000/api/sensors/data" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-03-20T15:30:00Z",
    "temperature": 24.5,
    "humidity": 58.2,
    "soil_moisture": 43.1
  }'
```

The backend also accepts an optional `device_id` field for hardware clients that want to identify a specific node explicitly.

## Burn History

```bash
curl "http://localhost:8000/api/burns/history"
```

## Satellite NDVI

```bash
curl "http://localhost:8000/api/satellite/ndvi?lat=33.7490&lon=-84.3880&start_date=2026-02-01&end_date=2026-03-20"
```

## Net Positive Metrics

```bash
curl "http://localhost:8000/api/metrics/net-positive?burn_id=1"
```
