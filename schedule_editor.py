from flask import Blueprint, session, request, jsonify, render_template
from datetime import date, datetime, time, timedelta
import uuid


schedule_editor = Blueprint("schedule_editor", __name__)


def to_json_safe(value):
    if isinstance(value, (datetime, date, time)):
        return str(value)
    if isinstance(value, timedelta):
        return str(value)
    return value


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


@schedule_editor.route("/schedule/update", methods=["POST"])
def update_schedule():
    data = request.get_json()
    uid = data.get("uid")

    schedule = session.get("schedule", [])

    for item in schedule:
        if item["uid"] == uid:
            item["day"] = int(data.get("day"))
            item["start_time"] = data.get("start_time")
            item["end_time"] = data.get("end_time")
            item["place"]["name"] = data.get("name")
            item["place"]["address"] = data.get("address")
            item["place"]["category"] = data.get("category")
            item["place"]["avg_stay_minutes"] = data.get("avg_stay_minutes")
            item["place"]["rating"] = data.get("rating")
            item["reason"] = data.get("reason")
            break

    session["schedule"] = schedule
    return jsonify({"success": True})


@schedule_editor.route("/schedule/delete", methods=["POST"])
def delete_schedule():
    data = request.get_json()
    uid = data.get("uid")

    schedule = session.get("schedule", [])
    schedule = [item for item in schedule if item["uid"] != uid]

    session["schedule"] = schedule
    return jsonify({"success": True})


@schedule_editor.route("/schedule/add", methods=["POST"])
def add_schedule():
    data = request.get_json()

    schedule = session.get("schedule", [])

    new_item = {
        "uid": str(uuid.uuid4()),
        "day": int(data.get("day")),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "place": {
            "id": 0,
            "name": data.get("name"),
            "address": data.get("address"),
            "category": data.get("category"),
            "latitude": data.get("latitude") or 33.3617,
            "longitude": data.get("longitude") or 126.5292,
            "dog_allowed": 1,
            "dog_size_allowed": "전체",
            "indoor_outdoor": "정보없음",
            "avg_stay_minutes": data.get("avg_stay_minutes"),
            "rating": data.get("rating"),
            "recommendation_type": "custom"
        },
        "reason": data.get("reason")
    }

    schedule.append(new_item)
    session["schedule"] = schedule

    return jsonify({"success": True})


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