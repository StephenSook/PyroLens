# burn_scorer.py

from typing import Dict, Any, List


def _score_temperature(temp_f: float) -> tuple[int, bool, str]:
    if 45 <= temp_f <= 75:
        return 25, True, "Temperature is within the target prescribed burn range."
    elif 40 <= temp_f <= 80:
        return 15, False, "Temperature is near the preferred range, but not ideal."
    else:
        return 0, False, "Temperature is outside the preferred prescribed burn range."


def _score_humidity(humidity_pct: float) -> tuple[int, bool, str]:
    if 25 <= humidity_pct <= 60:
        return 25, True, "Relative humidity supports controlled ignition and containment."
    elif 20 <= humidity_pct <= 65:
        return 15, False, "Relative humidity is borderline for safe burn conditions."
    else:
        return 0, False, "Relative humidity is outside the preferred safety range."


def _score_wind(wind_speed_mph: float) -> tuple[int, bool, str]:
    if 3 <= wind_speed_mph <= 15:
        return 25, True, "Wind speed is within the preferred operational range."
    elif 1 <= wind_speed_mph <= 18:
        return 15, False, "Wind speed is borderline for operations."
    else:
        return 0, False, "Wind speed is outside the preferred operational range."


def _score_soil_moisture(soil_moisture_pct: float) -> tuple[int, bool, str]:
    if soil_moisture_pct > 20:
        return 25, True, "Soil moisture is above the minimum safety threshold."
    elif 15 <= soil_moisture_pct <= 20:
        return 15, False, "Soil moisture is borderline for safer controlled conditions."
    else:
        return 0, False, "Soil moisture is too low for safer controlled conditions."


def _derive_recommendation(score: int, factors: dict, conditions: dict) -> tuple[str, str, int]:
    wind_speed = conditions["wind_speed_mph"]
    soil_moisture = conditions["soil_moisture_pct"]
    humidity = conditions["humidity_pct"]

    # Hard safety stops
    if wind_speed > 20 or soil_moisture < 12 or humidity <= 15:
        return "Unsafe", "High", 92

    if all(factors.values()) and score >= 90:
        return "Optimal", "Low", 85
    elif score >= 60:
        return "Marginal", "Moderate", 70
    else:
        return "Unsafe", "High", 88


def score_burn_window(
    temperature_f: float,
    humidity_pct: float,
    wind_speed_mph: float,
    soil_moisture_pct: float,
    wind_direction_deg: float | None = None,
) -> Dict[str, Any]:
    """
    Returns a rule-based burn window decision for the hackathon MVP.
    """

    total_score = 0
    reasoning: List[str] = []
    factors: Dict[str, bool] = {}

    temp_score, temp_ok, temp_reason = _score_temperature(temperature_f)
    total_score += temp_score
    factors["temperature_ok"] = temp_ok
    reasoning.append(temp_reason)

    humidity_score, humidity_ok, humidity_reason = _score_humidity(humidity_pct)
    total_score += humidity_score
    factors["humidity_ok"] = humidity_ok
    reasoning.append(humidity_reason)

    wind_score, wind_ok, wind_reason = _score_wind(wind_speed_mph)
    total_score += wind_score
    factors["wind_ok"] = wind_ok
    reasoning.append(wind_reason)

    soil_score, soil_ok, soil_reason = _score_soil_moisture(soil_moisture_pct)
    total_score += soil_score
    factors["soil_moisture_ok"] = soil_ok
    reasoning.append(soil_reason)

    conditions = {
        "temperature_f": temperature_f,
        "humidity_pct": humidity_pct,
        "wind_speed_mph": wind_speed_mph,
        "wind_direction_deg": wind_direction_deg,
        "soil_moisture_pct": soil_moisture_pct,
    }

    recommendation, risk_level, confidence_pct = _derive_recommendation(
        total_score, factors, conditions
    )

    return {
        "mode": "rule_based",
        "burn_score": total_score,
        "recommendation": recommendation,
        "risk_level": risk_level,
        "confidence_pct": confidence_pct,
        "reasoning": reasoning,
        "factors": factors,
        "conditions": conditions,
    }


if __name__ == "__main__":
    # quick test
    result = score_burn_window(
        temperature_f=68,
        humidity_pct=45,
        wind_speed_mph=8,
        soil_moisture_pct=32,
        wind_direction_deg=220,
    )
    print(result)