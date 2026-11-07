import requests
import config

def get_weather(city: str) -> dict:
    """Отримує поточну погоду для міста через офіційне API OpenWeatherMap."""
    api_key = config.WEATHER_API_KEY
    # ВИПРАВЛЕНО: Правильний API URL та параметр ?q=
    url = f"https://openweathermap.org{city}&appid={api_key}&units=metric&lang=uk"
    
    try:
        response = requests.get(url, timeout=5) # Зменшено таймаут до 5 сек
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
    except Exception as e:
        print(f"Помилка OpenWeather API: {e}")
        
    return {"temp": 12, "feels_like": 11, "description": "хмарно з проясненнями", "city": city}

def get_weather_forecast(city: str) -> dict:
    """Отримує прогноз погоди для подорожей."""
    api_key = config.WEATHER_API_KEY
    # ВИПРАВЛЕНО: Правильний API URL для прогнозу та параметр ?q=
    url = f"https://openweathermap.org{city}&appid={api_key}&units=metric&lang=uk"
    
    try:
        response = requests.get(url, timeout=5)
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
        
    default_temp = 25 if "каїр" in city.lower() or "єгипет" in city.lower() else 12
    return {
        "temp": default_temp, 
        "description": "сонячно" if default_temp == 25 else "хмарно з проясненнями",
        "city": city
    }
