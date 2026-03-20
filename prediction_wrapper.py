# prediction_wrapper.py

from typing import Dict, Any
from burn_scorer import score_burn_window


def celsius_to_fahrenheit(temp_c: float) -> float:
    return (temp_c * 9 / 5) + 32


def get_temperature_f(sensor_data: Dict[str, Any], weather_data: Dict[str, Any]) -> float:
    """
    Prefer weather temperature if available, otherwise convert sensor temp if needed.
    """
    if "temperature_f" in weather_data and weather_data["temperature_f"] is not None:
        return float(weather_data["temperature_f"])

    if "temperature_f" in sensor_data and sensor_data["temperature_f"] is not None:
        return float(sensor_data["temperature_f"])

    if "temperature_c" in sensor_data and sensor_data["temperature_c"] is not None:
        return celsius_to_fahrenheit(float(sensor_data["temperature_c"]))

    raise ValueError("No usable temperature value found.")


def get_humidity_pct(sensor_data: Dict[str, Any], weather_data: Dict[str, Any]) -> float:
    """
    Prefer weather humidity for regional conditions, fallback to sensor humidity.
    """
    if "humidity_pct" in weather_data and weather_data["humidity_pct"] is not None:
        return float(weather_data["humidity_pct"])

    if "humidity_pct" in sensor_data and sensor_data["humidity_pct"] is not None:
        return float(sensor_data["humidity_pct"])

    raise ValueError("No usable humidity value found.")


def get_wind_speed_mph(weather_data: Dict[str, Any]) -> float:
    if "wind_speed_mph" in weather_data and weather_data["wind_speed_mph"] is not None:
        return float(weather_data["wind_speed_mph"])
    raise ValueError("No usable wind speed value found.")


def get_wind_direction_deg(weather_data: Dict[str, Any]) -> float | None:
    if "wind_direction_deg" in weather_data and weather_data["wind_direction_deg"] is not None:
        return float(weather_data["wind_direction_deg"])
    return None


def get_soil_moisture_pct(sensor_data: Dict[str, Any]) -> float:
    if "soil_moisture_pct" in sensor_data and sensor_data["soil_moisture_pct"] is not None:
        return float(sensor_data["soil_moisture_pct"])
    raise ValueError("No usable soil moisture value found.")


def predict_burn_decision(sensor_data: Dict[str, Any], weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main wrapper Tylin/backend can call.
    """
    temperature_f = get_temperature_f(sensor_data, weather_data)
    humidity_pct = get_humidity_pct(sensor_data, weather_data)
    wind_speed_mph = get_wind_speed_mph(weather_data)
    wind_direction_deg = get_wind_direction_deg(weather_data)
    soil_moisture_pct = get_soil_moisture_pct(sensor_data)

    result = score_burn_window(
        temperature_f=temperature_f,
        humidity_pct=humidity_pct,
        wind_speed_mph=wind_speed_mph,
        soil_moisture_pct=soil_moisture_pct,
        wind_direction_deg=wind_direction_deg,
    )

    # Add a clean top-level response that frontend/backend can use directly
    return {
        "mode": result["mode"],
        "burn_score": result["burn_score"],
        "recommendation": result["recommendation"],
        "risk_level": result["risk_level"],
        "confidence_pct": result["confidence_pct"],
        "reasoning": result["reasoning"],
        "factors": result["factors"],
        "conditions": result["conditions"],
    }


if __name__ == "__main__":
    sensor_data = {
        "temperature_c": 20,
        "humidity_pct": 47,
        "soil_moisture_pct": 28,
    }

    weather_data = {
        "temperature_f": 69,
        "humidity_pct": 43,
        "wind_speed_mph": 7,
        "wind_direction_deg": 210,
    }

    output = predict_burn_decision(sensor_data, weather_data)
    print(output)