import os
import requests


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# 환경변수에 API 키를 안 넣었을 때 임시로 사용할 키
# 나중에는 보안을 위해 환경변수 방식으로 바꾸는 것이 좋음
if not OPENWEATHER_API_KEY:
    OPENWEATHER_API_KEY = "0119dea3d3052675c2499ca3e9d47db7"


def get_jeju_weather(travel_date):
    if not OPENWEATHER_API_KEY:
        return "날씨 정보 없음"

    url = "https://api.openweathermap.org/data/2.5/forecast"

    params = {
        "q": "Jeju,KR",
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "kr"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        print("날씨 API 상태코드:", response.status_code)
        print("날씨 API 메시지:", data.get("message"))

        if response.status_code != 200:
            return "날씨 정보 없음"

        selected_weather = None
        selected_temp = None

        # OpenWeather forecast는 보통 3시간 단위 예보를 list에 담아서 줌
        for item in data.get("list", []):
            forecast_date = item.get("dt_txt", "").split(" ")[0]

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

    except Exception as e:
        print("날씨 API 오류:", e)
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

    elif weather == "날씨 정보 없음":
        items += [
            "출발 전 날씨 확인",
            "우산 또는 방수용품"
        ]

    # 중복 제거
    return list(dict.fromkeys(items))