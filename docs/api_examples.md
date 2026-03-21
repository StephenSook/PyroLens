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
    "device_id": "esp32-node-001",
    "timestamp": "2026-03-20T15:30:00Z",
    "temperature": 72.4,
    "humidity": 41.2,
    "soil_moisture": 28.7,
    "wind_speed": 6.8
  }'
```

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
