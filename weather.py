import requests
import config

def get_weather(city: str) -> dict:
    """Отримує поточну погоду для міста через офіційне API OpenWeatherMap."""
    api_key = config.WEATHER_API_KEY
    
    # ЗМІНЕНО НА АКТУАЛЬНИЙ API ДОМЕН СЕРВЕРА
    url = f"https://openweathermap.org{city}&appid={api_key}&units=metric&lang=uk"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"],
                "city": data["name"],
                "humidity": data["main"]["humidity"],
                "wind": {"speed": data["wind"]["speed"]}
            }
        else:
            print(f"OpenWeather помилка {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Помилка OpenWeather API: {e}")
        
    return {"temp": 99, "feels_like": 99, "description": f"помилка сервера (Код {response.status_code if 'response' in locals() else 'Unknown'})", "city": city}

def get_weather_forecast(city: str) -> dict:
    """Отримує прогноз погоди для подорожей."""
    api_key = config.WEATHER_API_KEY
    
    # ЗМІНЕНО НА АКТУАЛЬНИЙ API ДОМЕН СЕРВЕРА ДЛЯ ПРОГНОЗУ
    url = f"https://openweathermap.org{city}&appid={api_key}&units=metric&lang=uk"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "list" in data and len(data["list"]) > 0:
                first_forecast = data["list"][0]
                return {
                    "temp": round(first_forecast["main"]["temp"]),
                    "feels_like": round(first_forecast["main"]["feels_like"]),
                    "description": first_forecast["weather"][0]["description"],
                    "city": data["city"]["name"]
                }
    except Exception as e:
        print(f"Помилка прогнозу погоди: {e}")
        
    return {"temp": 99, "description": "помилка прогнозу", "city": city}
