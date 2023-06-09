"""
    openweathermap.py

    Copyright (c) 2023 Martijn <martijn [at] mrtijn.nl>

    https://github.com/m-rtijn/openweathermap-exporter

    This file is part of openweathermap-exporter.

    openweathermap-exporter is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    openweathermap-exporter is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with openweathermap-exporter. If not, see <https://www.gnu.org/licenses/>.

    SPDX-License-Identifier: AGPL-3.0-or-later
"""

from datetime import datetime, timedelta
from functools import lru_cache
import json
from typing import Optional
import requests

GEOCODING_API_BASE_URL="http://api.openweathermap.org/geo/1.0/direct"
CURRENT_WEATHER_API_BASE_URL="https://api.openweathermap.org/data/2.5/weather"
CURRENT_AIR_POLLUTION_API_BASE_URL="http://api.openweathermap.org/data/2.5/air_pollution"

class Coordinate:
    """Class representing a coordinate defined by latitude and longitude."""

    lat: float
    lon: float

    def __init__(self, **kwargs):
        try:
            self.lat = kwargs["lat"]
            self.lon = kwargs["lon"]
        except KeyError:
            try:
                self.lat = kwargs["obj"]["lat"]
                self.lon = kwargs["obj"]["lon"]
            except KeyError:
                self.lat = kwargs["obj"]["latitude"]
                self.lon = kwargs["obj"]["longitude"]


    def __str__(self):
        return f"Coordinate(lat={self.lat}, lon={self.lon})"

class WeatherCondition:
    """Class representing one weather condition as provided by the OpenWeatherMap API.

    For more information, see https://openweathermap.org/weather-conditions
    """

    id: int
    main: str
    description: str
    icon_id: str

    def __init__(self, obj: dict):
        try:
            self.id = obj["id"]
        except:
            self.id = -999
        try:
            self.main = obj["main"]
        except:
            self.main = "Weather condition main not found"
        try:
            self.description = obj["description"]
        except:
            self.description = "Weather condititon description not found"
        try:
            self.icon_id = obj["icon"]
        except:
            self.icon_id = "Weather condition icon id not found"

    def __str__(self):
        return (f"WeatherCondition(id={self.icon_id},main={self.main},"
                f"description={self.description},icon_id={self.icon_id})")

class WeatherInformation:
    """Class representing weather information as provided by the OpenWeatherMap API."""
    coord: Coordinate
    weather_conditions: list[WeatherCondition] = []
    temp: float
    temp_feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    visibility: int
    wind_speed: float
    wind_deg: float
    wind_gust: Optional[float]
    cloudiness: float
    rain_volume_1h: float
    rain_volume_3h: float
    snow_volume_1h: float
    snow_volume_3h: float
    timestamp: datetime
    sunrise: datetime
    sunset: datetime

    def __init__(self, obj: dict):
        """
        Create WeatherInformation object from a dictionary result from the
        OpenWeatherMap CurrentWeather API.

        https://openweathermap.org/current
        """
        self.coord = Coordinate(obj=obj["coord"])

        for weather_condition_obj in obj["weather"]:
            self.weather_conditions.append(WeatherCondition(weather_condition_obj))

        self.temp = obj["main"]["temp"]
        self.temp_feels_like = obj["main"]["feels_like"]
        self.temp_max = obj["main"]["temp_max"]
        self.temp_min = obj["main"]["temp_min"]
        self.pressure = obj["main"]["pressure"]
        self.humidity = obj["main"]["humidity"]
        self.visibility = obj["visibility"]
        self.wind_deg = obj["wind"]["deg"]
        try:
            self.wind_gust = obj["wind"]["gust"]
        except KeyError:
            self.wind_gust = None
        self.wind_speed = obj["wind"]["speed"]
        self.cloudiness = obj["clouds"]["all"]
        try:
            self.rain_volume_1h = obj["rain"]["1h"]
        except KeyError:
            self.rain_volume_1h = 0
        try:
            self.rain_volume_3h = obj["rain"]["3h"]
        except KeyError:
            self.rain_volume_3h = 0
        try:
            self.snow_volume_1h = obj["snow"]["1h"]
        except KeyError:
            self.snow_volume_1h = 0
        try:
            self.snow_volume_3h = obj["snow"]["3h"]
        except KeyError:
            self.snow_volume_3h = 0
        self.timestamp = datetime.fromtimestamp(obj["dt"])
        self.sunrise = datetime.fromtimestamp(obj["sys"]["sunrise"])
        self.sunset = datetime.fromtimestamp(obj["sys"]["sunset"])

    def __str__(self):
        return (f"WeatherInformation(temp={self.temp}, humidity={self.humidity},"
                f"timestamp={self.timestamp}, coord={self.coord})")

class AirPollutionInformation:
    """Class representing air pollution information as provided by the OpenWeatherMap API."""
    coord: Coordinate
    timestamp: datetime

    # For meaning and possible values of this value,
    # see https://openweathermap.org/api/air-pollution
    air_quality_index: int
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float
    pm10: float
    nh3: float

    def __init__(self, obj: dict):
        """Parse air pollution information from the OpenWeatherMap Air Pollution API.

        https://openweathermap.org/api/air-pollution
        """

        self.coord = Coordinate(obj=obj["coord"])
        res_obj = obj["list"][0]
        self.timestamp = datetime.fromtimestamp(res_obj["dt"])
        self.air_quality_index = res_obj["main"]["aqi"]
        self.co = res_obj["components"]["co"]
        self.no = res_obj["components"]["no"]
        self.no2 = res_obj["components"]["no2"]
        self.o3 = res_obj["components"]["o3"]
        self.so2 = res_obj["components"]["so2"]
        self.pm2_5 = res_obj["components"]["pm2_5"]
        self.pm10 = res_obj["components"]["pm10"]
        self.nh3 = res_obj["components"]["nh3"]

    def __str__(self):
        return (f"AirPollutionInformation(timestamp={self.timestamp},"
                f"aqi={self.air_quality_index}, co={self.co}, no={self.no}, no2={self.no2},"
                f"o3={self.o3}, so2={self.so2}, pm2_5={self.pm2_5}, pm10={self.pm10},"
                f"nh3={self.nh3})")

class OpenWeatherMap:
    """Basic wrapper around the OpenWeatherMap APIs."""

    api_key: str
    api_calls_count: int = 0

    def __init__(self, api_key: str):
        self.api_key = api_key

    # TODO: Add request self-limiting
    def owm_api_request(self, base_url: str, parameters: dict, timeout_time=10) -> dict:
        """Do a request to an OpenWeatherMap API endpoint."""

        self.api_calls_count += 1

        parameters["appid"] = self.api_key

        resp = requests.get(base_url, params=parameters, timeout=timeout_time)

        return json.loads(resp.text)

    @lru_cache(maxsize=256)
    def get_coordinate(self, location_name: str, country_code: str) -> Coordinate:
        """Use Geocoding API to map a location_name and country_code to a coordinate.

        https://openweathermap.org/api/geocoding-api
        """

        parameters = {"q" : f"{location_name},{country_code}", "limit": 1}

        resp = self.owm_api_request(GEOCODING_API_BASE_URL, parameters)[0]

        return Coordinate(obj=resp)

    def get_current_weather(self, coord: Coordinate, units="metric") -> WeatherInformation:
        """Use Current Weather API to get current weather information.

        https://openweathermap.org/current
        """

        parameters = {"lat": coord.lat, "lon": coord.lon, "units": units}

        resp = self.owm_api_request(CURRENT_WEATHER_API_BASE_URL, parameters)

        return WeatherInformation(resp)

    def get_current_air_pollution(self, coord: Coordinate) -> AirPollutionInformation:
        """Use Current Air Pollution API to get current air pollution information.

        https://openweathermap.org/api/air-pollution
        """

        parameters = {"lat": coord.lat, "lon": coord.lon}

        resp = self.owm_api_request(CURRENT_AIR_POLLUTION_API_BASE_URL, parameters)

        return AirPollutionInformation(resp)

class OpenWeatherMapLocation:
    """A location about which weather information can be requested via the OpenWeatherMap API."""

    owm: OpenWeatherMap

    location_name: str
    country_code: str

    coord: Coordinate

    last_current_weather: Optional[WeatherInformation] = None
    last_current_air_pollution: Optional[AirPollutionInformation] = None

    def __init__(self, owm: OpenWeatherMap, **kwargs):
        """Create a new OpenWeatherMapLocation instance.

        location_name and country_code keyword arguments are required.
        If lat= and lon= are provided, these values will be used for the Coordinate,
        otherwise the OpenWeatherMap Geocode API will be used to get the coordinates."""
        self.location_name = kwargs["location_name"]
        self.country_code = kwargs["country_code"]
        self.owm = owm

        try:
            self.coord = Coordinate(lat=kwargs["lat"], lon=kwargs["lon"])
        except KeyError:
            self.coord = self.owm.get_coordinate(self.location_name, self.country_code)

    def __str__(self):
        return (f"OpenWeatherMapLocation(location_name={self.location_name},"
                f"country_code={self.country_code}, {self.coord})")

    def get_current_weather(self) -> WeatherInformation:
        """Get current weather information for this location.

        The information is cached internally, so that the OpenWeatherMap API
        will not be called more than once per location per ten minutes, since that
        is the internal update frequency of OpenWeatherMap.
            For more information, see https://openweathermap.org/appid#apicare.
        """

        if self.last_current_weather is None:
            self.last_current_weather = self.owm.get_current_weather(self.coord)
        else:
            time_since_last_update = datetime.now() - self.last_current_weather.timestamp
            if time_since_last_update > timedelta(minutes=10):
                self.last_current_weather = self.owm.get_current_weather(self.coord)

        return self.last_current_weather

    def get_current_air_pollution(self) -> AirPollutionInformation:
        """Get current air pollution information for this location.

        The information is cached internally, so that the OpenWeatherMap API
        will not be called more than once per location per ten minutes, since that
        is the internal update frequency of OpenWeatherMap.
            For more information, see https://openweathermap.org/appid#apicare.
        """

        if self.last_current_air_pollution is None:
            self.last_current_air_pollution = self.owm.get_current_air_pollution(self.coord)
        else:
            time_since_last_update = datetime.now() - self.last_current_air_pollution.timestamp
            if time_since_last_update > timedelta(minutes=10):
                self.last_current_air_pollution = self.owm.get_current_air_pollution(self.coord)

        return self.last_current_air_pollution
