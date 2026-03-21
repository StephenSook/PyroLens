"""Create or update a live sensor node location for ESP bridge ingestion.

Run from the backend directory:
    .venv/bin/python scripts/provision_sensor_node.py --lat 33.749 --lon -84.388
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

from geoalchemy2.elements import WKTElement

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.sensor_node import SensorNode  # noqa: E402


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Provision or update a sensor node for live ESP ingestion.")
    parser.add_argument("--device-id", default="serial-bridge-esp32", help="Device ID used by the bridge payload.")
    parser.add_argument("--site-name", default="Georgia Pilot Burn Site", help="Human-readable site name.")
    parser.add_argument("--status", default="online", help="Sensor status string to persist.")
    parser.add_argument("--lat", type=float, required=True, help="Sensor latitude.")
    parser.add_argument("--lon", type=float, required=True, help="Sensor longitude.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        sensor_node = db.query(SensorNode).filter(SensorNode.device_id == args.device_id).one_or_none()
        if sensor_node is None:
            sensor_node = SensorNode(device_id=args.device_id, site_name=args.site_name, status=args.status)
            db.add(sensor_node)

        sensor_node.site_name = args.site_name
        sensor_node.status = args.status
        sensor_node.location_geom = WKTElement(f"POINT({args.lon} {args.lat})", srid=4326)
        db.commit()
        print("Provisioned sensor node successfully.")
        print(f"device_id={args.device_id}")
        print(f"site_name={args.site_name}")
        print(f"coordinates=({args.lat}, {args.lon})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
