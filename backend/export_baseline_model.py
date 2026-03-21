"""Train and export the notebook baseline model for backend inference."""

from __future__ import annotations

from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import burn_scorer

MODEL_OUTPUT_PATH = Path(__file__).resolve().parent / "models" / "burn_model.pkl"
TRAINING_ROWS = 200


def build_training_frame(rows: int = TRAINING_ROWS) -> pd.DataFrame:
    """Replicate the notebook's synthetic baseline dataset generation."""

    data: list[dict[str, float | str]] = []
    rng = np.random.default_rng(42)

    for _ in range(rows):
        temp = float(rng.uniform(60, 90))
        humidity = float(rng.uniform(10, 70))
        wind = float(rng.uniform(0, 25))
        soil = float(rng.uniform(5, 40))
        wind_dir = float(rng.uniform(0, 360))

        result = burn_scorer.score_burn_window(
            temperature_f=temp,
            humidity_pct=humidity,
            wind_speed_mph=wind,
            soil_moisture_pct=soil,
            wind_direction_deg=wind_dir,
        )

        data.append(
            {
                "temperature_f": temp,
                "humidity_pct": humidity,
                "wind_speed_mph": wind,
                "soil_moisture_pct": soil,
                "wind_direction_deg": wind_dir,
                "burn_score": float(result["burn_score"]),
            }
        )

    return pd.DataFrame(data)


def train_and_export_model(output_path: Path = MODEL_OUTPUT_PATH) -> Path:
    """Train the baseline regressor and persist it for backend loading."""

    df = build_training_frame()
    feature_columns = [
        "temperature_f",
        "humidity_pct",
        "wind_speed_mph",
        "soil_moisture_pct",
        "wind_direction_deg",
    ]
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(df[feature_columns], df["burn_score"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)
    return output_path


if __name__ == "__main__":
    saved_path = train_and_export_model()
    print(f"Saved baseline model to {saved_path}")
