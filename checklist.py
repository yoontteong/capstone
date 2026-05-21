import os
import requests


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_jeju_weather(travel_date):
    if not OPENWEATHER_API_KEY:
        return "날씨 정보 없음"

    url = "https://api.openweathermap.org/data/2.5/forecast"

    params = {
    "q": "Jeju,KR",
    "appid": "0119dea3d3052675c2499ca3e9d47db7",
    "units": "metric",
    "lang": "kr"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code != 200:
            return "날씨 정보 없음"

        selected_weather = None
        selected_temp = None

        for item in data["list"]:
            forecast_date = item["dt_txt"].split(" ")[0]

            if forecast_date == travel_date:
                selected_weather = item["weather"][0]["main"]
                selected_temp = item["main"]["temp"]
                break

        if selected_weather is None:
            return "날씨 정보 없음"

        if selected_weather in ["Rain", "Drizzle", "Thunderstorm"]:
            return "비"

        if selected_weather == "Snow":
            return "눈"

        if selected_temp >= 28:
            return "더움"

        if selected_temp <= 5:
            return "추움"

        return "보통"

    except Exception:
        return "날씨 정보 없음"


def recommend_checklist(weather, stay, outdoor):
    items = [
        "사료",
        "물",
        "간식",
        "리드줄",
        "배변봉투"
    ]

    if stay == "yes":
        items += [
            "이동장",
            "담요",
            "배변패드"
        ]

    if outdoor == "yes":
        items += [
            "휴대용 물통",
            "돗자리"
        ]

    if weather == "비":
        items += [
            "강아지 우비",
            "수건"
        ]

    elif weather == "더움":
        items += [
            "쿨매트",
            "충분한 물"
        ]

    elif weather == "추움":
        items += [
            "보온용품",
            "담요"
        ]

    elif weather == "눈":
        items += [
            "방수용품",
            "수건",
            "보온용품"
        ]

    return list(dict.fromkeys(items))