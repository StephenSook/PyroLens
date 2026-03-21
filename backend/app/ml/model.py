"""Burn-window ML feature schema and model wrapper."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, TypedDict

from pydantic import BaseModel

try:
    import joblib
except ImportError:  # pragma: no cover - joblib ships with scikit-learn in normal installs.
    joblib = None

try:
    import pandas as pd
except ImportError:  # pragma: no cover - pandas is expected in the backend environment.
    pd = None


logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CORE_FEATURE_ORDER = (
    "temperature",
    "humidity",
    "wind_speed",
    "soil_moisture",
    "ndvi",
    "fuel_load_estimate",
    "time_since_last_burn_days",
)
FULL_FEATURE_ORDER = CORE_FEATURE_ORDER + ("latitude", "longitude", "month")
LEGACY_NOTEBOOK_FEATURE_ORDER = (
    "temperature_f",
    "humidity_pct",
    "wind_speed_mph",
    "soil_moisture_pct",
    "wind_direction_deg",
)
FEATURE_NAME_ALIASES = {
    "temperature_f": "temperature",
    "humidity_pct": "humidity",
    "wind_speed_mph": "wind_speed",
    "soil_moisture_pct": "soil_moisture",
}


class BurnWindowFeatures(BaseModel):
    """Feature vector used for burn-window success prediction."""

    temperature: float
    humidity: float
    wind_speed: float
    soil_moisture: float
    ndvi: float
    fuel_load_estimate: float
    time_since_last_burn_days: float
    latitude: float | None = None
    longitude: float | None = None
    month: int | None = None
    wind_direction_deg: float | None = None


class BurnWindowPrediction(TypedDict):
    """Normalized prediction payload returned by the model wrapper."""

    score: int
    recommendation: str
    prob_success: float
    raw_probability: float


class BurnWindowModel:
    """Wrapper around a serialized burn-window model with placeholder fallback."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._loaded_path: Path | None = None
        self._model_backend: str = "placeholder"
        self._placeholder_warning_emitted = False
        self._using_placeholder = True

    @property
    def loaded_path(self) -> str | None:
        """Return the resolved model path used during the latest load attempt."""

        return None if self._loaded_path is None else str(self._loaded_path)

    @property
    def model_backend(self) -> str:
        """Return the backend used for the currently active model."""

        return self._model_backend

    @property
    def using_placeholder(self) -> bool:
        """Return whether placeholder inference is currently active."""

        return self._using_placeholder

    def load_model(self, path: str) -> None:
        """Load a trained model from disk or fall back to placeholder mode."""

        model_path = self._resolve_model_path(path)
        self._loaded_path = model_path
        self._model = None
        self._model_backend = "placeholder"
        self._placeholder_warning_emitted = False
        self._using_placeholder = True

        if not model_path.exists():
            logger.warning(
                "Burn-window model file not found at %s; placeholder predictor is active",
                model_path,
            )
            return

        load_errors: list[str] = []
        loaders: list[tuple[str, Any]] = []
        if joblib is not None:
            loaders.append(("joblib", joblib.load))
        loaders.append(("pickle", self._load_with_pickle))

        for backend_name, loader in loaders:
            try:
                loaded_model = loader(model_path)
            except Exception as exc:  # pragma: no cover - depends on local model artifacts.
                load_errors.append(f"{backend_name}: {exc}")
                continue

            self._model = loaded_model
            self._model_backend = backend_name
            self._using_placeholder = False
            logger.info("Loaded burn-window model via %s from %s", backend_name, model_path)
            return

        logger.warning(
            "Failed to load burn-window model from %s; placeholder predictor is active. errors=%s",
            model_path,
            "; ".join(load_errors) if load_errors else "unknown",
        )

    def predict(self, features: BurnWindowFeatures) -> BurnWindowPrediction:
        """Predict burn-window success and normalize the output contract."""

        if self._model is None or self._using_placeholder:
            return self._predict_with_placeholder(features)

        raw_probability = self._predict_probability(features)
        score = int(round(raw_probability * 100))
        recommendation = self._score_to_recommendation(score)
        return {
            "score": score,
            "recommendation": recommendation,
            "prob_success": raw_probability,
            "raw_probability": raw_probability,
        }

    def _predict_probability(self, features: BurnWindowFeatures) -> float:
        """Run inference against a loaded estimator and return a probability."""

        inference_payload = self._build_inference_payload(features)

        if hasattr(self._model, "predict_proba"):
            probabilities = self._model.predict_proba(inference_payload)
            probability = float(probabilities[0][-1])
            return self._clamp_probability(probability)

        prediction = self._model.predict(inference_payload)
        value = float(prediction[0])
        if 0.0 <= value <= 1.0:
            return self._clamp_probability(value)
        if 0.0 <= value <= 100.0:
            return self._clamp_probability(value / 100.0)
        return self._clamp_probability(1.0 if value > 0.0 else 0.0)

    def _build_inference_payload(self, features: BurnWindowFeatures) -> Any:
        """Return model input in the most compatible format for the loaded estimator."""

        feature_vector = self._build_feature_vector(features)
        ordered_feature_names = self._get_model_feature_names()

        if pd is not None and getattr(self._model, "feature_names_in_", None) is not None:
            return pd.DataFrame([feature_vector], columns=list(ordered_feature_names))

        return [feature_vector]

    def _build_feature_vector(self, features: BurnWindowFeatures) -> list[float]:
        """Convert a feature model into the ordered numeric vector expected by the estimator."""

        payload = features.model_dump()
        ordered_feature_names = self._get_model_feature_names()
        return [self._coerce_feature_value(self._resolve_feature_value(name, payload)) for name in ordered_feature_names]

    def _get_model_feature_names(self) -> tuple[str, ...]:
        """Infer the expected feature ordering from the loaded estimator when possible."""

        if self._model is None:
            return FULL_FEATURE_ORDER

        feature_names = getattr(self._model, "feature_names_in_", None)
        if feature_names is not None:
            return tuple(str(name) for name in feature_names)

        n_features = getattr(self._model, "n_features_in_", None)
        if n_features == len(CORE_FEATURE_ORDER):
            return CORE_FEATURE_ORDER
        if n_features == len(LEGACY_NOTEBOOK_FEATURE_ORDER):
            return LEGACY_NOTEBOOK_FEATURE_ORDER
        if n_features == len(FULL_FEATURE_ORDER):
            return FULL_FEATURE_ORDER
        if isinstance(n_features, int) and 0 < n_features < len(FULL_FEATURE_ORDER):
            return FULL_FEATURE_ORDER[:n_features]

        return FULL_FEATURE_ORDER

    @staticmethod
    def _resolve_feature_value(feature_name: str, payload: dict[str, Any]) -> Any:
        """Map legacy notebook feature names onto the backend feature schema when needed."""

        if feature_name in payload:
            return payload[feature_name]

        aliased_name = FEATURE_NAME_ALIASES.get(feature_name)
        if aliased_name is not None:
            return payload.get(aliased_name)

        return None

    @staticmethod
    def _load_with_pickle(path: Path) -> Any:
        """Load a serialized model using the standard pickle module."""

        with path.open("rb") as model_file:
            return pickle.load(model_file)

    @staticmethod
    def _coerce_feature_value(value: Any) -> float:
        """Convert optional feature values into floats for estimator input."""

        if value is None:
            return 0.0
        return float(value)

    @staticmethod
    def _resolve_model_path(path: str) -> Path:
        """Resolve relative model paths from the backend root."""

        model_path = Path(path).expanduser()
        if model_path.is_absolute():
            return model_path
        return BACKEND_ROOT / model_path

    @staticmethod
    def _clamp_probability(value: float) -> float:
        """Clamp a probability into the inclusive 0-1 range."""

        return max(0.0, min(1.0, value))

    @staticmethod
    def _score_to_recommendation(score: int) -> str:
        """Map a 0-100 score onto the API recommendation labels."""

        if score >= 71:
            return "Optimal"
        if score >= 41:
            return "Marginal"
        return "Unsafe"

    def _predict_with_placeholder(self, features: BurnWindowFeatures) -> BurnWindowPrediction:
        """Return a deterministic placeholder prediction while no trained model is available."""

        if not self._placeholder_warning_emitted:
            logger.warning("Burn-window placeholder predictor is active")
            self._placeholder_warning_emitted = True

        # TODO: Replace this placeholder heuristic path with production model inference
        # backed by a trained artifact once one is available in deployment.
        weighted_probability = (
            0.26 * self._score_band(features.temperature, low=45.0, high=75.0)
            + 0.22 * self._score_band(features.humidity, low=25.0, high=60.0)
            + 0.22 * self._score_band(features.wind_speed, low=3.0, high=15.0)
            + 0.14 * self._score_minimum(features.soil_moisture, minimum=20.0)
            + 0.10 * self._score_minimum(features.ndvi, minimum=0.3)
            + 0.04 * self._score_band(features.fuel_load_estimate, low=0.5, high=6.0)
            + 0.02 * self._score_band(features.time_since_last_burn_days, low=180.0, high=1095.0)
        )

        raw_probability = self._clamp_probability(weighted_probability)
        score = int(round(raw_probability * 100))
        recommendation = self._score_to_recommendation(score)
        return {
            "score": score,
            "recommendation": recommendation,
            "prob_success": raw_probability,
            "raw_probability": raw_probability,
        }

    @staticmethod
    def _score_band(value: float, low: float, high: float) -> float:
        """Return a tapered score for a preferred numeric range."""

        if low <= value <= high:
            return 1.0

        span = max(high - low, 1.0)
        tolerance = span
        if value < low:
            return max(0.0, 1.0 - ((low - value) / tolerance))
        return max(0.0, 1.0 - ((value - high) / tolerance))

    @staticmethod
    def _score_minimum(value: float, minimum: float) -> float:
        """Return a bounded score for a minimum-threshold feature."""

        if value >= minimum:
            return 1.0
        if minimum <= 0:
            return 0.0
        return max(0.0, value / minimum)


burn_window_model = BurnWindowModel()
