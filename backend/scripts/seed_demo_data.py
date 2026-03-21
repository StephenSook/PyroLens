"""Seed deterministic demo data for the PyroLens dashboard.

Run from the backend directory:
    .venv/bin/python scripts/seed_demo_data.py
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from datetime import date, datetime, timezone
from pathlib import Path

from geoalchemy2.elements import WKTElement

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.burn import Burn  # noqa: E402
from app.models.net_positive_metric import NetPositiveMetric  # noqa: E402
from app.models.sensor_node import SensorNode  # noqa: E402
from app.models.sensor_reading import SensorReading  # noqa: E402


DEFAULT_DEVICE_ID = "serial-bridge-esp32"
DEFAULT_SITE_NAME = "Georgia Pilot Burn Site"
DEFAULT_COUNTY = "Fulton"
DEFAULT_LAT = 33.749
DEFAULT_LON = -84.388


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Seed demo burn history, metrics, and sensor data.")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID, help="Sensor device ID to seed/update.")
    parser.add_argument("--site-name", default=DEFAULT_SITE_NAME, help="Human-readable sensor site name.")
    parser.add_argument("--county", default=DEFAULT_COUNTY, help="County name used for demo burns.")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Seed site latitude.")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Seed site longitude.")
    return parser


def point_wkt(*, lat: float, lon: float) -> str:
    return f"POINT({lon} {lat})"


def square_polygon_wkt(*, lat: float, lon: float, half_size_deg: float) -> str:
    left = lon - half_size_deg
    right = lon + half_size_deg
    bottom = lat - half_size_deg
    top = lat + half_size_deg
    return (
        "POLYGON(("
        f"{left} {bottom}, "
        f"{right} {bottom}, "
        f"{right} {top}, "
        f"{left} {top}, "
        f"{left} {bottom}"
        "))"
    )


def build_demo_burns(*, county: str, lat: float, lon: float) -> list[dict[str, object]]:
    return [
        {
            "county": county,
            "burn_date": date(2025, 11, 14),
            "acreage": 240.0,
            "objective": "Fuel reduction and understory restoration",
            "outcome": "Contained and successful",
            "location_wkt": square_polygon_wkt(lat=lat, lon=lon, half_size_deg=0.03),
            "metrics": {
                "co2_prevented": 6200.0,
                "prescribed_emissions": 1450.0,
                "wildfire_baseline_emissions": 7650.0,
                "biodiversity_gain_index": 0.87,
                "fuel_load_reduction_pct": 42.5,
                "vegetation_recovery_curve": [
                    {"timestamp": "2025-11-14", "ndvi": 0.39},
                    {"timestamp": "2026-02-14", "ndvi": 0.46},
                    {"timestamp": "2026-05-14", "ndvi": 0.54},
                    {"timestamp": "2026-11-14", "ndvi": 0.63},
                ],
            },
        },
        {
            "county": county,
            "burn_date": date(2023, 3, 18),
            "acreage": 310.0,
            "objective": "Habitat maintenance",
            "outcome": "Completed within prescription",
            "location_wkt": square_polygon_wkt(lat=lat + 0.05, lon=lon - 0.04, half_size_deg=0.025),
        },
        {
            "county": county,
            "burn_date": date(2021, 2, 9),
            "acreage": 180.0,
            "objective": "Firebreak reinforcement",
            "outcome": "Completed with minor smoke holdover",
            "location_wkt": square_polygon_wkt(lat=lat - 0.06, lon=lon + 0.05, half_size_deg=0.02),
        },
    ]


def upsert_burn(db, burn_data: dict[str, object]) -> Burn:
    burn = (
        db.query(Burn)
        .filter(Burn.county == burn_data["county"])
        .filter(Burn.burn_date == burn_data["burn_date"])
        .filter(Burn.objective == burn_data["objective"])
        .one_or_none()
    )
    if burn is None:
        burn = Burn(
            county=str(burn_data["county"]),
            burn_date=burn_data["burn_date"],
            acreage=float(burn_data["acreage"]),
            objective=str(burn_data["objective"]),
            outcome=str(burn_data["outcome"]),
            location_geom=WKTElement(str(burn_data["location_wkt"]), srid=4326),
        )
        db.add(burn)
        db.flush()
        return burn

    burn.acreage = float(burn_data["acreage"])
    burn.outcome = str(burn_data["outcome"])
    burn.location_geom = WKTElement(str(burn_data["location_wkt"]), srid=4326)
    db.flush()
    return burn


def upsert_metric(db, burn: Burn, metric_data: dict[str, object]) -> None:
    metric = db.query(NetPositiveMetric).filter(NetPositiveMetric.burn_id == burn.id).one_or_none()
    if metric is None:
        metric = NetPositiveMetric(burn_id=burn.id)
        db.add(metric)

    metric.co2_prevented = float(metric_data["co2_prevented"])
    metric.prescribed_emissions = float(metric_data["prescribed_emissions"])
    metric.wildfire_baseline_emissions = float(metric_data["wildfire_baseline_emissions"])
    metric.biodiversity_gain_index = float(metric_data["biodiversity_gain_index"])
    metric.fuel_load_reduction_pct = float(metric_data["fuel_load_reduction_pct"])
    metric.vegetation_recovery_curve = list(metric_data["vegetation_recovery_curve"])


def upsert_sensor_node(db, *, device_id: str, site_name: str, lat: float, lon: float) -> SensorNode:
    sensor_node = db.query(SensorNode).filter(SensorNode.device_id == device_id).one_or_none()
    if sensor_node is None:
        sensor_node = SensorNode(device_id=device_id, site_name=site_name, status="online")
        db.add(sensor_node)

    sensor_node.site_name = site_name
    sensor_node.status = "online"
    sensor_node.location_geom = WKTElement(point_wkt(lat=lat, lon=lon), srid=4326)
    db.flush()
    return sensor_node


def upsert_sensor_reading(db, *, sensor_id: int, device_id: str) -> None:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    existing = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor_id)
        .filter(SensorReading.timestamp == timestamp)
        .one_or_none()
    )
    raw_payload = {
        "device_id": device_id,
        "temperature": 71.2,
        "humidity": 41.8,
        "soil_moisture": 33.5,
        "wind_speed": 6.4,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
    }
    if existing is None:
        db.add(
            SensorReading(
                sensor_id=sensor_id,
                timestamp=timestamp,
                temperature=71.2,
                humidity=41.8,
                soil_moisture=33.5,
                wind_speed=6.4,
                raw_payload=raw_payload,
            )
        )
        return

    existing.temperature = 71.2
    existing.humidity = 41.8
    existing.soil_moisture = 33.5
    existing.wind_speed = 6.4
    existing.raw_payload = raw_payload


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        burns = build_demo_burns(county=args.county, lat=args.lat, lon=args.lon)
        for burn_data in burns:
            burn = upsert_burn(db, burn_data)
            metric_data = burn_data.get("metrics")
            if isinstance(metric_data, dict):
                upsert_metric(db, burn, metric_data)

        sensor_node = upsert_sensor_node(
            db,
            device_id=args.device_id,
            site_name=args.site_name,
            lat=args.lat,
            lon=args.lon,
        )
        upsert_sensor_reading(db, sensor_id=sensor_node.id, device_id=args.device_id)
        db.commit()
        print("Seeded demo data successfully.")
        print(f"Sensor device_id: {args.device_id}")
        print(f"Sensor site: {args.site_name} @ ({args.lat}, {args.lon})")
        print(f"Burn records: {len(burns)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
