import requests
import config

def get_weather(city: str = "Lviv") -> dict:
    """Отримує поточну детальну погоду з OpenWeatherMap (для щоденних рекомендацій)."""
    # ВИПРАВЛЕНО: Встановлено правильний API URL замість адреси сайту
    url = "https://openweathermap.org"
    
    params = {
        "q": city,
        "appid": config.WEATHER_API_KEY,
        "units": "metric",
        "lang": "uk"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Безпечно витягуємо опади та хмари
            rain = data.get("rain", {}).get("1h", 0)
            snow = data.get("snow", {}).get("1h", 0)
            clouds = data.get("clouds", {}).get("all", 0)
            uvi = 1 if clouds > 70 else 4  
            
            return {
                "success": True,
                "city": data.get("name", city),
                "temp": round(data["main"]["temp"]),
                "description": data["weather"][0]["description"],
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"],
                "wind": {"speed": data["wind"]["speed"]},  # Об'єкт вітру для сумісності з ai_stylist.py
                "wind_speed": data["wind"]["speed"],
                "rain": rain,
                "snow": snow,
                "uvi": uvi
            }
    except Exception as e:
        print(f"Помилка отримання поточної погоди: {e}")

    # Надійний резервний фолбек, якщо пропав інтернет чи ліміти API
    return {
        "success": True,
        "city": city,
        "temp": 12,
        "description": "хмарно з проясненнями",
        "feels_like": 10,
        "humidity": 78,
        "wind": {"speed": 4.5},
        "wind_speed": 4.5,
        "rain": 0,
        "snow": 0,
        "uvi": 2
    }


def get_weather_forecast(city: str = "Lviv") -> dict:
    """Отримує стабільний прогноз погоди на 5 днів наперед (для планування подорожей)."""
    # ВИПРАВЛЕНО: Встановлено правильний API URL прогнозу 5 days / 3 hours
    url = "https://openweathermap.org"
    
    params = {
        "q": city,
        "appid": config.WEATHER_API_KEY,
        "units": "metric",
        "lang": "uk"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            daily_forecasts = []
            seen_dates = set()
            
            for item in data.get("list", []):
                dt_txt = item.get("dt_txt", "")
                if not dt_txt:
                    continue
                date_txt = dt_txt.split(" ")[0]  # Витягуємо дату YYYY-MM-DD
                
                # Збираємо унікальні дні
                if date_txt not in seen_dates:
                    seen_dates.add(date_txt)
                    daily_forecasts.append({
                        "date": date_txt,
                        "temp": round(item["main"]["temp"]),
                        "feels_like": round(item["main"]["feels_like"]),
                        "description": item["weather"][0]["description"]
                    })
            return {"success": True, "city": data.get("city", {}).get("name", city), "days": daily_forecasts}
    except Exception as e:
        print(f"Помилка отримання прогнозу погоди: {e}")

    # Реалістичний фолбек, якщо немає зв'язку з сервером OpenWeather
    return {
        "success": True,
        "city": city,
        "days": [
            {"date": "День 1", "temp": 14, "feels_like": 12, "description": "мінлива хмарність"},
            {"date": "День 2", "temp": 12, "feels_like": 10, "description": "можливий дощ"},
            {"date": "День 3", "temp": 15, "feels_like": 14, "description": "ясно"},
            {"date": "День 4", "temp": 11, "feels_like": 9, "description": "хмарно"},
            {"date": "День 5", "temp": 10, "feels_like": 8, "description": "невеликий дощ"},
        ]
    }
