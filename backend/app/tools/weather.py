from app.domain.enums import DataSourceType
from app.domain.models import WeatherLookupInput, WeatherResult
from app.tools.base import Tool


class MockWeatherLookupTool(Tool[WeatherLookupInput, WeatherResult]):
    name = "weather_lookup"
    description = "Simulated seasonal weather for planning. Not a live forecast."
    input_model = WeatherLookupInput

    async def _run(self, payload: WeatherLookupInput) -> WeatherResult:
        loc = payload.location.lower()
        month = 11
        if "-" in payload.date:
            try:
                month = int(payload.date.split("-")[1])
            except (IndexError, ValueError):
                month = 11
        if "cairo" in loc or "egypt" in loc or "giza" in loc:
            rainy = month in {1, 2, 3, 12}
            return WeatherResult(
                location=payload.location,
                date=payload.date,
                condition="mild with possible showers" if rainy else "clear and dry",
                temp_c=18.0 if rainy else 24.0,
                precipitation_chance=0.25 if rainy else 0.05,
                source_type=DataSourceType.mock,
                notes="Mock climatology for Cairo; not a live forecast.",
            )
        if "hurghada" in loc or "sharm" in loc or "sahel" in loc or "north coast" in loc:
            return WeatherResult(
                location=payload.location,
                date=payload.date,
                condition="clear and dry",
                temp_c=26.0 if month in {11, 12, 1, 2, 3} else 32.0,
                precipitation_chance=0.05,
                source_type=DataSourceType.mock,
                notes="Mock Red Sea / coast climatology; not a live forecast.",
            )
        return WeatherResult(
            location=payload.location,
            date=payload.date,
            condition="unknown (no mock climatology)",
            temp_c=20.0,
            precipitation_chance=0.2,
            source_type=DataSourceType.mock,
            notes="Location not in mock dataset.",
        )


class RealWeatherLookupTool(Tool[WeatherLookupInput, WeatherResult]):
    name = "weather_lookup"
    description = "Live forecast from Open-Meteo."
    input_model = WeatherLookupInput

    async def _run(self, payload: WeatherLookupInput) -> WeatherResult:
        from app.tools.live_apis import open_meteo_weather

        data = await open_meteo_weather(payload.location, payload.date)
        return WeatherResult(
            location=payload.location,
            date=payload.date,
            condition=data["condition"],
            temp_c=data["temp_c"],
            precipitation_chance=data["precipitation_chance"],
            source_type=DataSourceType.live,
            notes="Open-Meteo forecast",
        )
