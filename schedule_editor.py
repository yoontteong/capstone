from flask import Blueprint, session, request, jsonify, render_template
from datetime import date, datetime, time, timedelta
from db import get_connection
from config import KAKAO_REST_API_KEY
import requests
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


# 장소명으로 장소 정보 조회
# 1) DB에 같은 장소가 있으면 DB 정보 사용
# 2) DB에 없으면 카카오 로컬 API로 제주 장소 검색
def get_place_info(name):
    if not name:
        return None

    # 1. DB에서 먼저 검색
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT name, address, latitude, longitude
        FROM places
        WHERE name = %s
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
        LIMIT 1
        """,
        (name,)
    )

    place = cursor.fetchone()
    cursor.close()
    conn.close()

    if place:
        return {
            "name": place["name"],
            "address": place.get("address") or "",
            "latitude": float(place["latitude"]),
            "longitude": float(place["longitude"])
        }

    # 2. DB에 없으면 카카오 장소 검색 API 사용
    if not KAKAO_REST_API_KEY:
        return None

    try:
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={
                "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
            },
            params={
                "query": f"제주 {name}"
            },
            timeout=5
        )

        print("카카오 상태코드:", response.status_code)
        print("카카오 응답:", response.text)

        response.raise_for_status()
        documents = response.json().get("documents", [])

        if not documents:
            return None

        # 제주 주소가 포함된 결과를 우선 사용
        selected = next(
            (doc for doc in documents
             if "제주" in (doc.get("road_address_name") or doc.get("address_name") or "")),
            documents[0]
        )

        return {
            "name": selected.get("place_name") or name,
            "address": selected.get("road_address_name") or selected.get("address_name") or "",
            "latitude": float(selected["y"]),
            "longitude": float(selected["x"])
        }

    except Exception as e:
        print("카카오 장소 검색 오류:", e)
        return None


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

            name = data.get("name")
            place_info = get_place_info(name)

            if not place_info:
                return jsonify({
                    "success": False,
                    "message": "장소를 찾지 못했습니다. 장소명을 조금 더 정확하게 입력해주세요."
                }), 400

            item["place"]["name"] = place_info["name"]
            item["place"]["address"] = place_info["address"]
            item["place"]["category"] = data.get("category")
            item["place"]["avg_stay_minutes"] = data.get("avg_stay_minutes")

            # 사용자가 추천점수 입력 안 하게 할 것이므로 기본값 유지
            item["place"]["rating"] = item["place"].get("rating", 4.0)
            item["place"]["latitude"] = place_info["latitude"]
            item["place"]["longitude"] = place_info["longitude"]

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

    name = data.get("name")
    place_info = get_place_info(name)

    if not place_info:
        return jsonify({
            "success": False,
            "message": "장소를 찾지 못했습니다. 장소명을 조금 더 정확하게 입력해주세요."
        }), 400

    new_item = {
        "uid": str(uuid.uuid4()),
        "day": int(data.get("day")),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "place": {
            "id": 0,
            "name": place_info["name"],
            "address": place_info["address"],
            "category": data.get("category"),
            "latitude": place_info["latitude"],
            "longitude": place_info["longitude"],
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