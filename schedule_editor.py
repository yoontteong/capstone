from flask import Blueprint, session, request, jsonify, render_template
from datetime import date, datetime, time, timedelta
import uuid

schedule_editor = Blueprint("schedule_editor", __name__)


# 날짜/시간 타입을 JSON 저장 가능한 문자열로 변환
def to_json_safe(value):
    if isinstance(value, (datetime, date, time)):
        return str(value)
    if isinstance(value, timedelta):
        return str(value)
    return value


# 기존 추천 일정에 uid 부여
def normalize_schedule(schedule):
    normalized = []

    for item in schedule:
        place = item.get("place", {})
        safe_place = {}

        for key, value in place.items():
            safe_place[key] = to_json_safe(value)

        normalized.append({
            "uid": str(uuid.uuid4()),
            "day": item.get("day"),
            "start_time": item.get("start_time"),
            "end_time": item.get("end_time"),
            "place": safe_place,
            "reason": item.get("reason")
        })

    return normalized


# 주소 기반 좌표 변환 자리
# 지금은 시간이 없으니 제주 중심 기본 좌표 사용
def get_coordinates_by_address(address):
    default_latitude = 33.3617
    default_longitude = 126.5292

    return default_latitude, default_longitude


# 일정 수정
@schedule_editor.route("/schedule/update", methods=["POST"])
def update_schedule():
    data = request.get_json()
    uid = data.get("uid")

    schedule = session.get("schedule", [])

    for item in schedule:
        if item.get("uid") == uid:
            item["day"] = int(data.get("day"))
            item["start_time"] = data.get("start_time")
            item["end_time"] = data.get("end_time")

            item["place"]["name"] = data.get("name")
            item["place"]["address"] = data.get("address")
            item["place"]["category"] = data.get("category")
            item["place"]["avg_stay_minutes"] = data.get("avg_stay_minutes")

            # 사용자가 추천점수 입력 안 하게 할 것이므로 기본값 유지
            item["place"]["rating"] = item["place"].get("rating", 4.0)

            # 주소가 바뀌었을 수 있으니 기본 좌표 재설정
            latitude, longitude = get_coordinates_by_address(data.get("address"))
            item["place"]["latitude"] = latitude
            item["place"]["longitude"] = longitude

            item["reason"] = data.get("reason")
            break

    session["schedule"] = schedule

    return jsonify({"success": True})


# 일정 삭제
@schedule_editor.route("/schedule/delete", methods=["POST"])
def delete_schedule():
    data = request.get_json()
    uid = data.get("uid")

    schedule = session.get("schedule", [])
    schedule = [item for item in schedule if item.get("uid") != uid]

    session["schedule"] = schedule

    return jsonify({"success": True})


# 일정 직접 추가
@schedule_editor.route("/schedule/add", methods=["POST"])
def add_schedule():
    data = request.get_json()

    schedule = session.get("schedule", [])

    address = data.get("address")
    latitude, longitude = get_coordinates_by_address(address)

    new_item = {
        "uid": str(uuid.uuid4()),
        "day": int(data.get("day")),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "place": {
            "id": 0,
            "name": data.get("name"),
            "address": address,
            "category": data.get("category"),
            "latitude": latitude,
            "longitude": longitude,
            "dog_allowed": 1,
            "dog_size_allowed": "전체",
            "indoor_outdoor": "정보없음",
            "avg_stay_minutes": data.get("avg_stay_minutes"),
            "rating": 4.0,
            "recommendation_type": "custom"
        },
        "reason": data.get("reason")
    }

    schedule.append(new_item)
    session["schedule"] = schedule

    return jsonify({"success": True})


# 수정된 일정 결과 화면
@schedule_editor.route("/ai-schedule/edited", methods=["GET"])
def edited_schedule_result():
    schedule = session.get("schedule", [])
    pattern = session.get("pattern", {})
    travel_info = session.get("travel_info", {})

    return render_template(
        "ai_schedule_result.html",
        travel_period=travel_info.get("travel_period"),
        style=travel_info.get("style"),
        transport_type=travel_info.get("transport_type"),
        dog_size=travel_info.get("dog_size"),
        dog_personality=travel_info.get("dog_personality"),
        schedule=schedule,
        pattern=pattern
    )