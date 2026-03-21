"""Import historical burn polygons and optional metrics from GeoJSON.

Run from the backend directory:
    .venv/bin/python scripts/import_burns_geojson.py path/to/burns.geojson
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402


REQUIRED_BURN_KEYS = ("county", "burn_date", "acreage", "objective", "outcome")
FLAT_METRIC_KEYS = (
    "co2_prevented",
    "prescribed_emissions",
    "wildfire_baseline_emissions",
    "biodiversity_gain_index",
    "fuel_load_reduction_pct",
    "vegetation_recovery_curve",
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Import burn history into Supabase from GeoJSON.")
    parser.add_argument("geojson_path", help="Path to a GeoJSON FeatureCollection file.")
    return parser


def load_geojson(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    if payload.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON must be a FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("GeoJSON FeatureCollection must include a features array")
    return payload


def validate_feature(feature: dict[str, Any], index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict):
        raise ValueError(f"Feature {index} is missing properties")
    if not isinstance(geometry, dict):
        raise ValueError(f"Feature {index} is missing geometry")
    missing_keys = [key for key in REQUIRED_BURN_KEYS if key not in properties]
    if missing_keys:
        raise ValueError(f"Feature {index} is missing required properties: {', '.join(missing_keys)}")

    date.fromisoformat(str(properties["burn_date"]))
    float(properties["acreage"])
    return properties, geometry


def extract_metric_payload(properties: dict[str, Any]) -> dict[str, Any] | None:
    nested_metrics = properties.get("net_positive_metrics")
    if isinstance(nested_metrics, dict):
        return nested_metrics

    if all(key in properties for key in FLAT_METRIC_KEYS):
        return {key: properties[key] for key in FLAT_METRIC_KEYS}
    return None


def upsert_burn(connection, *, properties: dict[str, Any], geometry: dict[str, Any]) -> int:
    existing_id = connection.execute(
        text(
            """
            SELECT id
            FROM burns
            WHERE county = :county
              AND burn_date = :burn_date
              AND objective = :objective
            ORDER BY id
            LIMIT 1
            """
        ),
        {
            "county": str(properties["county"]),
            "burn_date": str(properties["burn_date"]),
            "objective": str(properties["objective"]),
        },
    ).scalar_one_or_none()

    params = {
        "geometry": json.dumps(geometry),
        "county": str(properties["county"]),
        "burn_date": str(properties["burn_date"]),
        "acreage": float(properties["acreage"]),
        "objective": str(properties["objective"]),
        "outcome": str(properties["outcome"]),
    }

    if existing_id is None:
        return int(
            connection.execute(
                text(
                    """
                    INSERT INTO burns (location_geom, county, burn_date, acreage, objective, outcome)
                    VALUES (
                        ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326),
                        :county,
                        :burn_date,
                        :acreage,
                        :objective,
                        :outcome
                    )
                    RETURNING id
                    """
                ),
                params,
            ).scalar_one()
        )

    connection.execute(
        text(
            """
            UPDATE burns
            SET location_geom = ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326),
                county = :county,
                burn_date = :burn_date,
                acreage = :acreage,
                objective = :objective,
                outcome = :outcome
            WHERE id = :burn_id
            """
        ),
        {**params, "burn_id": existing_id},
    )
    return int(existing_id)


def upsert_metric(connection, *, burn_id: int, metric_payload: dict[str, Any]) -> None:
    existing_id = connection.execute(
        text("SELECT id FROM net_positive_metrics WHERE burn_id = :burn_id LIMIT 1"),
        {"burn_id": burn_id},
    ).scalar_one_or_none()

    params = {
        "burn_id": burn_id,
        "co2_prevented": float(metric_payload["co2_prevented"]),
        "prescribed_emissions": float(metric_payload["prescribed_emissions"]),
        "wildfire_baseline_emissions": float(metric_payload["wildfire_baseline_emissions"]),
        "biodiversity_gain_index": float(metric_payload["biodiversity_gain_index"]),
        "fuel_load_reduction_pct": float(metric_payload["fuel_load_reduction_pct"]),
        "vegetation_recovery_curve": json.dumps(metric_payload["vegetation_recovery_curve"]),
    }

    if existing_id is None:
        connection.execute(
            text(
                """
                INSERT INTO net_positive_metrics (
                    burn_id,
                    co2_prevented,
                    prescribed_emissions,
                    wildfire_baseline_emissions,
                    biodiversity_gain_index,
                    fuel_load_reduction_pct,
                    vegetation_recovery_curve
                )
                VALUES (
                    :burn_id,
                    :co2_prevented,
                    :prescribed_emissions,
                    :wildfire_baseline_emissions,
                    :biodiversity_gain_index,
                    :fuel_load_reduction_pct,
                    CAST(:vegetation_recovery_curve AS jsonb)
                )
                """
            ),
            params,
        )
        return

    connection.execute(
        text(
            """
            UPDATE net_positive_metrics
            SET co2_prevented = :co2_prevented,
                prescribed_emissions = :prescribed_emissions,
                wildfire_baseline_emissions = :wildfire_baseline_emissions,
                biodiversity_gain_index = :biodiversity_gain_index,
                fuel_load_reduction_pct = :fuel_load_reduction_pct,
                vegetation_recovery_curve = CAST(:vegetation_recovery_curve AS jsonb)
            WHERE id = :metric_id
            """
        ),
        {**params, "metric_id": existing_id},
    )


def main() -> None:
    args = build_parser().parse_args()
    payload = load_geojson(args.geojson_path)
    features = payload["features"]

    db = SessionLocal()
    imported_burns = 0
    imported_metrics = 0
    try:
        with db.begin():
            connection = db.connection()
            for index, feature in enumerate(features, start=1):
                properties, geometry = validate_feature(feature, index)
                burn_id = upsert_burn(connection, properties=properties, geometry=geometry)
                imported_burns += 1

                metric_payload = extract_metric_payload(properties)
                if metric_payload is not None:
                    upsert_metric(connection, burn_id=burn_id, metric_payload=metric_payload)
                    imported_metrics += 1
        print("Imported burn GeoJSON successfully.")
        print(f"Burn records processed: {imported_burns}")
        print(f"Net positive metric records processed: {imported_metrics}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
