import requests

API_KEY = open("weather.key", 'r').read()

class WeatherAPIClass:
    @staticmethod
    def OnDay   (CITY, DATE):
        # Формат YYYY-MM-DD
        url = f"https://api.weatherapi.com/v1/history.json?key={API_KEY}&q={CITY}&dt={DATE}"

        response = requests.get(url)
        data = response.json()

        if "forecast" in data:
            forecast = data["forecast"]["forecastday"][0]["hour"]

            def get_temp_by_hour_range(start, end):
                temps = [hour["temp_c"] for hour in forecast if start <= int(hour["time"].split()[1].split(":")[0]) <= end]
                return round(sum(temps) / len(temps), 1) if temps else None

            morning_temp = get_temp_by_hour_range(6, 10)   # 6:00–10:59
            day_temp     = get_temp_by_hour_range(11, 17)  # 12:00–17:59
            evening_temp = get_temp_by_hour_range(18, 23)  # 18:00–23:59

            return {"morning": morning_temp, "day": day_temp, "evening": evening_temp}
        else:
            return None


WeatherAPI = WeatherAPIClass()
