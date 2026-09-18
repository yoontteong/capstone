import uuid

import json

import requests

from flask import (
    Flask,
    render_template,
    request,
    session,
    jsonify,
    redirect
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from ai_scheduler import generate_ai_schedule
from checklist import get_jeju_weather, recommend_checklist
from schedule_editor import (
    schedule_editor,
    normalize_schedule,
    get_place_info
)
from community import community
from db import get_connection
from activity.service import calculate_activity_summary
from config import KAKAO_REST_API_KEY


app = Flask(__name__)
app.secret_key = "pinksole_secret_key"

app.register_blueprint(schedule_editor)
app.register_blueprint(community)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/checklist")
def checklist_page():
    return render_template("checklist/checklist.html")


@app.route("/checklist-result", methods=["POST"])
def checklist_result():

    if "user_id" not in session:
        return redirect("/login")

    travel_date = request.form.get("travel_date")
    stay = request.form.get("stay")
    outdoor = request.form.get("outdoor")

    weather = get_jeju_weather(travel_date)

    items = recommend_checklist(
        weather=weather,
        stay=stay,
        outdoor=outdoor
    )

    # 체크리스트 제목 자동 생성
    title = f"{travel_date} 제주 여행"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 체크리스트 본체 저장
        cursor.execute("""
            INSERT INTO checklists (
                user_id,
                title,
                travel_date,
                stay,
                outdoor,
                weather
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            title,
            travel_date,
            stay,
            outdoor,
            str(weather)
        ))

        checklist_id = cursor.lastrowid

        # 추천 준비물 각각 저장
        for index, item in enumerate(items, start=1):

            cursor.execute("""
                INSERT INTO checklist_items (
                    checklist_id,
                    item_name,
                    is_checked,
                    sort_order
                )
                VALUES (%s, %s, %s, %s)
            """, (
                checklist_id,
                item,
                False,
                index
            ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("체크리스트 저장 오류:", e)

        return "체크리스트 저장 중 오류가 발생했습니다.", 500

    finally:
        cursor.close()
        conn.close()

    return redirect(f"/checklist/{checklist_id}")

@app.route("/checklist/<int:checklist_id>")
def checklist_detail(checklist_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 현재 로그인한 사용자의 체크리스트인지 확인
    cursor.execute("""
        SELECT
            id,
            title,
            travel_date,
            stay,
            outdoor,
            weather,
            created_at
        FROM checklists
        WHERE id = %s
          AND user_id = %s
    """, (
        checklist_id,
        session["user_id"]
    ))

    checklist = cursor.fetchone()

    if not checklist:
        cursor.close()
        conn.close()
        return "체크리스트를 찾을 수 없습니다.", 404

    # 준비물 조회
    cursor.execute("""
        SELECT
            id,
            item_name,
            is_checked,
            sort_order
        FROM checklist_items
        WHERE checklist_id = %s
        ORDER BY sort_order ASC, id ASC
    """, (checklist_id,))

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "checklist/checklist_result.html",
        checklist=checklist,
        items=items
    )

@app.route("/checklist/item/toggle", methods=["POST"])
def checklist_item_toggle():

    if "user_id" not in session:
        return jsonify({
            "success": False
        }), 401

    data = request.get_json()

    item_id = data.get("item_id")
    is_checked = data.get("is_checked")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE checklist_items ci
        JOIN checklists c
            ON ci.checklist_id = c.id
        SET ci.is_checked = %s
        WHERE ci.id = %s
          AND c.user_id = %s
    """, (
        is_checked,
        item_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True
    })

@app.route("/checklist/item/add", methods=["POST"])
def checklist_item_add():

    if "user_id" not in session:
        return jsonify({
            "success": False
        }), 401

    data = request.get_json()

    checklist_id = data.get("checklist_id")
    item_name = data.get("item_name")

    if not item_name:
        return jsonify({
            "success": False,
            "message": "준비물 이름이 없습니다."
        }), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 내 체크리스트인지 확인
    cursor.execute("""
        SELECT id
        FROM checklists
        WHERE id = %s
          AND user_id = %s
    """, (
        checklist_id,
        session["user_id"]
    ))

    checklist = cursor.fetchone()

    if not checklist:
        cursor.close()
        conn.close()

        return jsonify({
            "success": False
        }), 403

    # 현재 마지막 순서 확인
    cursor.execute("""
        SELECT COALESCE(MAX(sort_order), 0) AS max_order
        FROM checklist_items
        WHERE checklist_id = %s
    """, (checklist_id,))

    result = cursor.fetchone()

    next_order = result["max_order"] + 1

    cursor.execute("""
        INSERT INTO checklist_items (
            checklist_id,
            item_name,
            is_checked,
            sort_order
        )
        VALUES (%s, %s, %s, %s)
    """, (
        checklist_id,
        item_name,
        False,
        next_order
    ))

    item_id = cursor.lastrowid

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "item_id": item_id
    })

@app.route("/checklist/item/delete", methods=["POST"])
def checklist_item_delete():

    if "user_id" not in session:
        return jsonify({
            "success": False
        }), 401

    data = request.get_json()

    item_id = data.get("item_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE ci
        FROM checklist_items ci
        JOIN checklists c
            ON ci.checklist_id = c.id
        WHERE ci.id = %s
          AND c.user_id = %s
    """, (
        item_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True
    })

@app.route("/checklist/delete/<int:checklist_id>", methods=["POST"])
def checklist_delete(checklist_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM checklists
        WHERE id = %s
          AND user_id = %s
    """, (
        checklist_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/checklists")

@app.route("/checklists")
def checklist_list():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.id,
            c.title,
            c.travel_date,
            c.weather,
            c.created_at,
            COUNT(ci.id) AS total_count,
            SUM(CASE WHEN ci.is_checked = 1 THEN 1 ELSE 0 END) AS checked_count
        FROM checklists c
        LEFT JOIN checklist_items ci
            ON c.id = ci.checklist_id
        WHERE c.user_id = %s
        GROUP BY
            c.id,
            c.title,
            c.travel_date,
            c.weather,
            c.created_at
        ORDER BY c.created_at DESC
    """, (session["user_id"],))

    checklists = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "checklist/checklist_list.html",
        checklists=checklists
    )

@app.route("/ai-schedule", methods=["GET"])
def ai_schedule_form():

    if "user_id" not in session:
        return redirect("/login")

    # /ai-schedule?dog_id=1 에서 dog_id 받기
    dog_id = request.args.get("dog_id")

    if not dog_id:
        return redirect("/trip/create")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 선택한 반려견이 실제 로그인 사용자의 반려견인지 확인
    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            personality
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    cursor.close()
    conn.close()

    if not dog:
        return "반려견 정보를 찾을 수 없습니다.", 404

    return render_template(
        "schedule/ai_schedule.html",
        dog=dog
    )

@app.route("/ai-schedule/result", methods=["POST"])
def ai_schedule_result():

    if "user_id" not in session:
        return redirect("/login")
    
    start_date = request.form.get("start_date")
    travel_period = request.form.get("travel_period")
    style = request.form.get("style")
    transport_type = request.form.get("transport_type")
    dog_id = request.form.get("dog_id")

    if not dog_id:
        return "반려견을 선택해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            personality
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    cursor.close()
    conn.close()

    if not dog:
        return "반려견 정보를 찾을 수 없습니다.", 404

    size_map = {
        "소형견": "소형",
        "중형견": "중형",
        "대형견": "대형"
    }

    dog_size = size_map.get(
        dog["size_category"],
        dog["size_category"]
    )

    dog_personality = dog["personality"]

    schedule, pattern = generate_ai_schedule(
        dog_size=dog_size,
        dog_personality=dog_personality,
        style=style,
        travel_period=travel_period,
        transport_type=transport_type
    )

    schedule = normalize_schedule(schedule)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    for item in schedule:
        place = item.get("place", {})

        place_id = place.get("id")

        if not place_id:
            place["review_avg"] = None
            place["review_count"] = 0
            continue

        cursor.execute("""
            SELECT
                AVG(rating) AS review_avg,
                COUNT(*) AS review_count
            FROM reviews
            WHERE place_id = %s
        """, (place_id,))

        review_info = cursor.fetchone()

        if review_info:
            place["review_avg"] = (
                round(float(review_info["review_avg"]), 1)
                if review_info["review_avg"] is not None
                else None
            )

            place["review_count"] = review_info["review_count"]
        else:
            place["review_avg"] = None
            place["review_count"] = 0

    cursor.close()
    conn.close()

    session["schedule"] = schedule
    session["pattern"] = pattern
    session["travel_info"] = {
        "start_date": start_date,
        "travel_period": travel_period,
        "style": style,
        "transport_type": transport_type,
        "dog_id": dog["id"],
        "dog_name": dog["name"],
        "dog_size": dog_size,
        "dog_personality": dog_personality
    }

    return render_template(
        "schedule/ai_schedule_result.html",
        start_date=start_date,
        travel_period=travel_period,
        style=style,
        transport_type=transport_type,
        dog_name=dog["name"],
        dog_size=dog_size,
        dog_personality=dog_personality,
        schedule=schedule,
        pattern=pattern
    )

@app.route("/trip/save-ai", methods=["POST"])
def save_ai_trip():

    if "user_id" not in session:
        return redirect("/login")

    schedule = session.get("schedule", [])
    travel_info = session.get("travel_info", {})
    pattern = session.get("pattern", {})

    if not schedule:
        return "저장할 여행 일정이 없습니다.", 400

    dog_id = travel_info.get("dog_id")
    start_date = travel_info.get("start_date")
    travel_period = travel_info.get("travel_period")
    style = travel_info.get("style")
    transport_type = travel_info.get("transport_type")

    if not dog_id:
        return "반려견 정보가 없습니다.", 400

    if not start_date:
        return "여행 시작일 정보가 없습니다.", 400


    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ==============================
        # 반려견 확인
        # ==============================

        cursor.execute("""
            SELECT
                id,
                name
            FROM dogs
            WHERE id = %s
              AND user_id = %s
        """, (
            dog_id,
            session["user_id"]
        ))

        dog = cursor.fetchone()

        if not dog:
            return "반려견 정보를 찾을 수 없습니다.", 404


        # ==============================
        # 여행 제목
        # ==============================

        title = f"{dog['name']}와 함께하는 제주 여행"


        # ==============================
        # trips 저장
        # ==============================

        cursor.execute("""
            INSERT INTO trips (
                user_id,
                dog_id,
                title,
                travel_period,
                style,
                transport_type,
                start_date,
                schedule_type,
                ai_pattern
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            session["user_id"],
            dog_id,
            title,
            travel_period,
            style,
            transport_type,
            start_date,
            "AI",
            json.dumps(
                pattern,
                ensure_ascii=False
            )
        ))

        trip_id = cursor.lastrowid


        # ==============================
        # DAY별 일정 저장
        # ==============================

        day_sequences = {}


        for item in schedule:

            day_number = int(
                item.get("day") or 1
            )


            day_sequences.setdefault(
                day_number,
                0
            )

            day_sequences[day_number] += 1

            sequence_no = (
                day_sequences[day_number]
            )


            place = item.get(
                "place",
                {}
            )

            place_id = place.get("id")


            # places 테이블에 존재하는
            # 장소만 place_id 사용
            if not place_id:
                place_id = None


            start_time = item.get(
                "start_time"
            )

            end_time = item.get(
                "end_time"
            )

            reason = item.get(
                "reason"
            )


            cursor.execute("""
                INSERT INTO trip_schedule_items (
                    trip_id,
                    day_number,
                    sequence_no,
                    place_id,
                    start_time,
                    end_time,
                    reason
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
            """, (
                trip_id,
                day_number,
                sequence_no,
                place_id,
                start_time,
                end_time,
                reason
            ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "AI 여행 저장 오류:",
            e
        )

        return (
            "여행 저장 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect("/trips")

@app.route("/trip/<int:trip_id>/ai")
def saved_ai_trip_detail(trip_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # 여행 기본 정보
        cursor.execute("""
            SELECT
                t.id,
                t.title,
                t.travel_period,
                t.style,
                t.transport_type,
                t.start_date,
                t.schedule_type,
                t.ai_pattern,

                d.id AS dog_id,
                d.name AS dog_name,
                d.size_category,
                d.personality

            FROM trips t

            JOIN dogs d
                ON t.dog_id = d.id

            WHERE t.id = %s
              AND t.user_id = %s
              AND t.schedule_type = 'AI'
        """, (
            trip_id,
            session["user_id"]
        ))

        trip = cursor.fetchone()

        if not trip:
            return "AI 여행 정보를 찾을 수 없습니다.", 404


        # 저장된 일정
        cursor.execute("""
            SELECT
                tsi.id,
                tsi.day_number,
                tsi.sequence_no,
                tsi.start_time,
                tsi.end_time,
                tsi.reason,

                p.id AS place_id,
                p.name,
                p.address,
                p.category,
                p.latitude,
                p.longitude,
                p.dog_allowed,
                p.dog_size_allowed,
                p.indoor_outdoor,
                p.avg_stay_minutes,
                p.rating,
                p.recommendation_type

            FROM trip_schedule_items tsi

            LEFT JOIN places p
                ON tsi.place_id = p.id

            WHERE tsi.trip_id = %s

            ORDER BY
                tsi.day_number,
                tsi.sequence_no
        """, (trip_id,))

        rows = cursor.fetchall()


        # ai_schedule_result.html이 기대하는
        # schedule 구조로 다시 복원
        schedule = []

        for row in rows:

            schedule.append({
                "uid": f"saved-{row['id']}",

                "day": row["day_number"],

                "start_time": (
                    str(row["start_time"])[:5]
                    if row["start_time"]
                    else ""
                ),

                "end_time": (
                    str(row["end_time"])[:5]
                    if row["end_time"]
                    else ""
                ),

                "place": {
                    "id": row["place_id"],
                    "name": row["name"],
                    "address": row["address"],
                    "category": row["category"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "dog_allowed": row["dog_allowed"],
                    "dog_size_allowed": row["dog_size_allowed"],
                    "indoor_outdoor": row["indoor_outdoor"],
                    "avg_stay_minutes": row["avg_stay_minutes"],
                    "rating": row["rating"],
                    "recommendation_type": row["recommendation_type"],

                    # 일단 후기 정보는 기본값
                    "review_avg": None,
                    "review_count": 0
                },

                "reason": row["reason"]
            })


        # JSON 컬럼이면 커넥터에 따라
        # dict 또는 문자열로 들어올 수 있음
        pattern = trip["ai_pattern"] or {}

        if isinstance(pattern, str):
            pattern = json.loads(pattern)


        size_map = {
            "소형견": "소형",
            "중형견": "중형",
            "대형견": "대형"
        }

        dog_size = size_map.get(
            trip["size_category"],
            trip["size_category"]
        )


        return render_template(
            "schedule/ai_schedule_result.html",

            start_date=trip["start_date"],
            travel_period=trip["travel_period"],
            style=trip["style"],
            transport_type=trip["transport_type"],

            dog_name=trip["dog_name"],
            dog_size=dog_size,
            dog_personality=trip["personality"],

            schedule=schedule,
            pattern=pattern,

            saved_trip=True,
            trip_id=trip_id
        )


    finally:

        cursor.close()
        conn.close()

@app.route("/trips")
def trip_list():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            t.id,
            t.title,
            t.travel_period,
            t.style,
            t.transport_type,
            t.start_date,
            t.schedule_type,
            t.created_at,
            d.name AS dog_name,

            COUNT(tsi.id) AS schedule_count

        FROM trips t

        JOIN dogs d
            ON t.dog_id = d.id

        LEFT JOIN trip_schedule_items tsi
            ON t.id = tsi.trip_id

        WHERE t.user_id = %s

        GROUP BY
            t.id,
            t.title,
            t.travel_period,
            t.style,
            t.transport_type,
            t.start_date,
            t.schedule_type,
            t.created_at,
            d.name

        ORDER BY
            t.start_date DESC,
            t.created_at DESC
    """, (session["user_id"],))

    trips = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "trip/trip_list.html",
        trips=trips
    )

@app.route("/trip/<int:trip_id>")
def trip_detail(trip_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 여행 기본정보 + 반려견 정보
        cursor.execute("""
            SELECT
                t.id,
                t.title,
                t.travel_period,
                t.style,
                t.transport_type,
                t.start_date,
                t.schedule_type,
                t.created_at,

                d.id AS dog_id,
                d.name AS dog_name,
                d.breed AS dog_breed,
                d.size_category AS dog_size,
                d.personality AS dog_personality

            FROM trips t

            JOIN dogs d
                ON t.dog_id = d.id

            WHERE t.id = %s
              AND t.user_id = %s
        """, (
            trip_id,
            session["user_id"]
        ))

        trip = cursor.fetchone()

        if not trip:
            return "여행 정보를 찾을 수 없습니다.", 404


        # 여행에 포함된 일정 조회
        cursor.execute("""
            SELECT
                tsi.id AS schedule_item_id,
                tsi.day_number,
                tsi.sequence_no,
                tsi.start_time,
                tsi.end_time,

                p.id AS place_id,
                p.name AS place_name,
                p.category,
                p.address,
                p.latitude,
                p.longitude

            FROM trip_schedule_items tsi

            JOIN places p
                ON tsi.place_id = p.id

            WHERE tsi.trip_id = %s

            ORDER BY
                tsi.day_number ASC,
                tsi.sequence_no ASC
        """, (trip_id,))

        schedule_items = cursor.fetchall()


        # DAY별 일정으로 묶기
        schedule_by_day = {}

        for item in schedule_items:

            day = item["day_number"]

            if day not in schedule_by_day:
                schedule_by_day[day] = []

            schedule_by_day[day].append(item)


        return render_template(
            "trip/trip_detail.html",
            trip=trip,
            schedule_by_day=schedule_by_day
        )

    finally:

        cursor.close()
        conn.close()

@app.route("/trip/manual", methods=["GET"])
def manual_trip_form():

    if "user_id" not in session:
        return redirect("/login")

    dog_id = request.args.get("dog_id")

    if not dog_id:
        return redirect("/trip/create")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            personality
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    cursor.close()
    conn.close()

    if not dog:
        return "반려견 정보를 찾을 수 없습니다.", 404

    return render_template(
        "trip/trip_manual.html",
        dog=dog
    )

@app.route("/trip/manual/editor", methods=["POST"])
def manual_trip_editor():

    if "user_id" not in session:
        return redirect("/login")

    dog_id = request.form.get("dog_id")
    title = request.form.get("title")
    start_date = request.form.get("start_date")
    travel_period = request.form.get("travel_period")
    transport_type = request.form.get("transport_type")

    if not dog_id:
        return redirect("/trip/create")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            personality
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    cursor.close()
    conn.close()

    if not dog:
        return "반려견 정보를 찾을 수 없습니다.", 404

    # 여행 기간에 따라 DAY 개수 설정
    day_count_map = {
        "당일치기": 1,
        "1박2일": 2,
        "2박3일": 3
    }

    day_count = day_count_map.get(travel_period, 1)

    # 직접 만든 일정 임시 저장
    session["manual_trip"] = {
        "dog_id": int(dog_id),
        "dog_name": dog["name"],
        "title": title,
        "start_date": start_date,
        "travel_period": travel_period,
        "transport_type": transport_type,
        "day_count": day_count,
        "schedule": []
    }

    return render_template(
        "trip/trip_manual_editor.html",
        dog=dog,
        title=title,
        start_date=start_date,
        travel_period=travel_period,
        transport_type=transport_type,
        day_count=day_count,
        schedule=[]
    )

@app.route("/trip/manual/schedule/add", methods=["POST"])
def add_manual_schedule():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    data = request.get_json()

    day = data.get("day")
    name = data.get("name")
    address = data.get("address")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    category = data.get("category")

    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not day or not name:
        return jsonify({
            "success": False,
            "message": "장소를 선택해주세요."
        }), 400

    manual_trip = session.get("manual_trip")

    if not manual_trip:
        return jsonify({
            "success": False,
            "message": "작성 중인 여행 정보가 없습니다."
        }), 400

    new_item = {
        "uid": str(uuid.uuid4()),
        "day": int(day),
        "start_time": start_time,
        "end_time": end_time,

        "place": {
            "id": None,
            "name": name,
            "address": address or "",
            "latitude": latitude,
            "longitude": longitude,
            "category": category or ""
        }
    }

    manual_trip["schedule"].append(new_item)

    session["manual_trip"] = manual_trip

    return jsonify({
        "success": True,
        "item": new_item
    })

@app.route("/trip/manual/schedule/delete", methods=["POST"])
def delete_manual_schedule():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    data = request.get_json()
    uid = data.get("uid")

    if not uid:
        return jsonify({
            "success": False,
            "message": "삭제할 일정 정보가 없습니다."
        }), 400

    manual_trip = session.get("manual_trip")

    if not manual_trip:
        return jsonify({
            "success": False,
            "message": "작성 중인 여행 정보가 없습니다."
        }), 400

    schedule = manual_trip.get("schedule", [])

    manual_trip["schedule"] = [
        item
        for item in schedule
        if item.get("uid") != uid
    ]

    session["manual_trip"] = manual_trip

    return jsonify({
        "success": True
    })

@app.route("/trip/<int:trip_id>/schedule/<int:item_id>/delete", methods=["POST"])
def delete_saved_manual_schedule(trip_id, item_id):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 이 여행이 현재 사용자의 수동 여행인지 확인
        cursor.execute("""
            SELECT id
            FROM trips
            WHERE id = %s
              AND user_id = %s
              AND schedule_type = 'MANUAL'
        """, (
            trip_id,
            session["user_id"]
        ))

        trip = cursor.fetchone()

        if not trip:
            return jsonify({
                "success": False,
                "message": "여행 정보를 찾을 수 없습니다."
            }), 404


        cursor.execute("""
            DELETE FROM trip_schedule_items
            WHERE id = %s
              AND trip_id = %s
        """, (
            item_id,
            trip_id
        ))


        # 삭제 후 DAY별 sequence_no 다시 정리
        cursor.execute("""
            SELECT
                id,
                day_number
            FROM trip_schedule_items
            WHERE trip_id = %s
            ORDER BY
                day_number,
                sequence_no
        """, (trip_id,))

        rows = cursor.fetchall()

        day_sequences = {}

        for row in rows:

            day = row["day_number"]

            day_sequences.setdefault(day, 0)
            day_sequences[day] += 1

            cursor.execute("""
                UPDATE trip_schedule_items
                SET sequence_no = %s
                WHERE id = %s
            """, (
                day_sequences[day],
                row["id"]
            ))


        conn.commit()

        return jsonify({
            "success": True
        })


    except Exception as e:

        conn.rollback()

        print("저장된 일정 삭제 오류:", e)

        return jsonify({
            "success": False,
            "message": "일정 삭제 중 오류가 발생했습니다."
        }), 500


    finally:

        cursor.close()
        conn.close()

@app.route("/trip/manual/place/search", methods=["GET"])
def search_manual_place():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    keyword = request.args.get("q", "").strip()

    if not keyword:
        return jsonify({
            "success": False,
            "message": "검색어를 입력해주세요."
        }), 400

    try:

        print("카카오 REST API KEY:", repr(KAKAO_REST_API_KEY))

        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={
                "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
            },
            params={
                "query": f"제주 {keyword}",
                "size": 15
            },
            timeout=5
        )

        print("카카오 상태:", response.status_code)
        print("카카오 응답:", response.text)
        response.raise_for_status()

        documents = response.json().get("documents", [])

        places = []

        for doc in documents:

            address = (
                doc.get("road_address_name")
                or doc.get("address_name")
                or ""
            )

            # 제주 지역 결과만 사용
            if "제주" not in address:
                continue

            places.append({
                "name": doc.get("place_name", ""),
                "address": address,
                "latitude": float(doc["y"]),
                "longitude": float(doc["x"]),
                "category": doc.get("category_name", "")
            })

        return jsonify({
            "success": True,
            "places": places
        })

    except Exception as e:

        print("수동 일정 장소 검색 오류:", e)

        return jsonify({
            "success": False,
            "message": "장소 검색 중 오류가 발생했습니다."
        }), 500

@app.route("/trip/manual/save", methods=["POST"])
def save_manual_trip():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    manual_trip = session.get("manual_trip")

    if not manual_trip:
        return jsonify({
            "success": False,
            "message": "저장할 여행 정보가 없습니다."
        }), 400

    schedule = manual_trip.get("schedule", [])

    if not schedule:
        return jsonify({
            "success": False,
            "message": "일정을 하나 이상 추가해주세요."
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # -----------------------------------
        # 1. trips 테이블에 여행 생성
        # -----------------------------------

        cursor.execute("""
            INSERT INTO trips (
                user_id,
                dog_id,
                title,
                travel_period,
                style,
                transport_type,
                start_date,
                schedule_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            manual_trip["dog_id"],
            manual_trip["title"],
            manual_trip["travel_period"],
            None,
            manual_trip["transport_type"],
            manual_trip["start_date"],
            "MANUAL"
        ))

        trip_id = cursor.lastrowid


        # -----------------------------------
        # 2. DAY → 시간순 정렬
        # -----------------------------------

        sorted_schedule = sorted(
            schedule,
            key=lambda item: (
                int(item.get("day", 1)),
                item.get("start_time") or "99:99"
            )
        )

        day_sequences = {}


        # -----------------------------------
        # 3. 각각의 장소 처리
        # -----------------------------------

        for item in sorted_schedule:

            place = item.get("place", {})

            name = place.get("name")
            address = place.get("address") or ""
            latitude = place.get("latitude")
            longitude = place.get("longitude")
            category = place.get("category") or "기타"


            # -------------------------------
            # 기존 places에 있는지 확인
            # -------------------------------

            cursor.execute("""
                SELECT id
                FROM places
                WHERE name = %s
                  AND (
                      address = %s
                      OR (
                          latitude = %s
                          AND longitude = %s
                      )
                  )
                LIMIT 1
            """, (
                name,
                address,
                latitude,
                longitude
            ))

            existing_place = cursor.fetchone()


            if existing_place:

                place_id = existing_place["id"]

            else:

                # ---------------------------
                # places에 새 장소 저장
                # ---------------------------

                cursor.execute("""
                    INSERT INTO places (
                        name,
                        category,
                        address,
                        latitude,
                        longitude,
                        dog_allowed,
                        dog_size_allowed,
                        indoor_outdoor,
                        rating,
                        recommendation_type
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """, (
                    name,
                    category,
                    address,
                    latitude,
                    longitude,
                    1,
                    "전체",
                    "정보없음",
                    None,
                    "custom"
                ))

                place_id = cursor.lastrowid


            # -------------------------------
            # DAY 안에서 순서 번호 계산
            # -------------------------------

            day = int(item.get("day", 1))

            if day not in day_sequences:
                day_sequences[day] = 1

            sequence_no = day_sequences[day]

            day_sequences[day] += 1


            # -------------------------------
            # trip_schedule_items 저장
            # -------------------------------

            cursor.execute("""
                INSERT INTO trip_schedule_items (
                    trip_id,
                    day_number,
                    sequence_no,
                    place_id,
                    start_time,
                    end_time
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                trip_id,
                day,
                sequence_no,
                place_id,
                item.get("start_time") or None,
                item.get("end_time") or None
            ))


        # 전부 성공했을 때만 실제 저장
        conn.commit()

        # 임시 작성 정보 제거
        session.pop("manual_trip", None)

        return jsonify({
            "success": True,
            "trip_id": trip_id
        })


    except Exception as e:

        if conn:
            conn.rollback()

        print("수동 여행 저장 오류:", e)

        return jsonify({
            "success": False,
            "message": "여행을 저장하는 중 오류가 발생했습니다."
        }), 500


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()    

@app.route("/trip/create")
def trip_create():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            personality
        FROM dogs
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (
        session["user_id"],
    ))

    dogs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "trip/trip_create.html",
        dogs=dogs
    )



#기록측정추가
@app.route("/activity")
def activity():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category
        FROM dogs
        WHERE user_id = %s
        ORDER BY id ASC
    """, (
        session["user_id"],
    ))

    dogs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "activity/activity.html",
        dogs=dogs
    )

@app.route("/activity/save", methods=["POST"])
def save_activity():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    data = request.get_json()

    dog_id = data.get("dog_id")
    distance_km = data.get("distance_km")
    duration_seconds = data.get("duration_seconds")
    average_speed = data.get("average_speed")
    positions = data.get("positions", [])

    if not dog_id:
        return jsonify({
            "success": False,
            "message": "반려견 정보가 없습니다."
        }), 400

    if not positions:
        return jsonify({
            "success": False,
            "message": "GPS 기록이 없습니다."
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    # 현재 로그인 사용자의 반려견인지 확인
    cursor.execute("""
        SELECT id
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    if not dog:
        cursor.close()
        conn.close()

        return jsonify({
            "success": False,
            "message": "등록된 반려견을 찾을 수 없습니다."
        }), 403

    try:
        # 활동 기록 저장
        cursor.execute("""
            INSERT INTO activity_records (
                dog_id,
                distance_km,
                duration_seconds,
                average_speed
            )
            VALUES (%s, %s, %s, %s)
        """, (
            dog_id,
            distance_km,
            duration_seconds,
            average_speed
        ))

        activity_id = cursor.lastrowid

        # GPS 좌표 저장
        for index, point in enumerate(positions, start=1):

            cursor.execute("""
                INSERT INTO activity_points (
                    activity_id,
                    sequence_no,
                    latitude,
                    longitude,
                    recorded_at
                )
                VALUES (%s, %s, %s, %s, NOW())
            """, (
                activity_id,
                index,
                point["lat"],
                point["lng"]
            ))

        conn.commit()

        return jsonify({
            "success": True,
            "activity_id": activity_id
        })

    except Exception as e:
        conn.rollback()

        print("활동 기록 저장 오류:", e)

        return jsonify({
            "success": False,
            "message": "활동 기록 저장 중 오류가 발생했습니다."
        }), 500

    finally:
        cursor.close()
        conn.close()

        

@app.route("/activity/history")
def activity_history():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ar.id,
            ar.activity_date,
            ar.distance_km,
            ar.duration_seconds,
            ar.average_speed,
            d.name AS dog_name,
            d.breed,
            d.size_category
        FROM activity_records ar
        JOIN dogs d
            ON ar.dog_id = d.id
        WHERE d.user_id = %s
        ORDER BY ar.activity_date DESC
    """, (
        session["user_id"],
    ))

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "activity/activity_history.html",
        records=records
    )


@app.route("/activity/history/<int:activity_id>")
def activity_detail(activity_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ar.id,
            ar.activity_date,
            ar.distance_km,
            ar.duration_seconds,
            ar.average_speed,
            d.name AS dog_name,
            d.breed,
            d.size_category
        FROM activity_records ar
        JOIN dogs d
            ON ar.dog_id = d.id
        WHERE ar.id = %s
          AND d.user_id = %s
    """, (
        activity_id,
        session["user_id"]
    ))

    record = cursor.fetchone()

    if not record:
        cursor.close()
        conn.close()
        return "활동 기록을 찾을 수 없습니다.", 404

    cursor.execute("""
        SELECT
            sequence_no,
            latitude,
            longitude,
            recorded_at
        FROM activity_points
        WHERE activity_id = %s
        ORDER BY sequence_no ASC
    """, (activity_id,))

    points = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "activity/activity_detail.html",
        record=record,
        points=points
    )

@app.route("/activity/summary/<int:dog_id>")
def activity_summary(dog_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    cursor.close()
    conn.close()

    if not dog:
        return "반려견을 찾을 수 없습니다.", 404

    summary = calculate_activity_summary(
        dog_id
    )

    if not summary:
        return "활동 기록이 없습니다.", 404

    return render_template(
        "activity/activity_summary.html",
        summary=summary
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    # 회원가입 화면
    if request.method == "GET":
        return render_template("auth/register.html")

    # 입력값 받기
    username = request.form.get("username")
    password = request.form.get("password")
    nickname = request.form.get("nickname")

    # 비밀번호 해시
    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 이미 존재하는 아이디인지 확인
    cursor.execute(
        "SELECT id FROM users WHERE username = %s",
        (username,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()

        return "이미 사용 중인 아이디입니다."

    # 회원 저장
    cursor.execute("""
        INSERT INTO users (
            username,
            password,
            nickname
        )
        VALUES (%s, %s, %s)
    """, (
        username,
        hashed_password,
        nickname
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return "회원가입이 완료되었습니다."

@app.route("/login", methods=["GET", "POST"])
def login():

    # 로그인 화면
    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            username,
            password,
            nickname
        FROM users
        WHERE username = %s
    """, (username,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    # 아이디가 없거나 비밀번호가 틀린 경우
    if not user or not check_password_hash(
        user["password"],
        password
    ):
        return "아이디 또는 비밀번호가 올바르지 않습니다."

    # 로그인 성공
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["nickname"] = user["nickname"]

    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("nickname", None)

    return redirect("/")

@app.route("/dog/register", methods=["GET", "POST"])
def dog_register():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    # 반려견 등록 화면
    if request.method == "GET":
        return render_template("dog/dog_register.html")

    name = request.form.get("name")
    breed = request.form.get("breed")
    size_category = request.form.get("size_category")
    birth_date = request.form.get("birth_date")
    personality = request.form.get("personality")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO dogs (
            user_id,
            name,
            breed,
            size_category,
            birth_date,
            personality
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        name,
        breed,
        size_category,
        birth_date if birth_date else None,
        personality
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dogs")    

@app.route("/dogs")
def dog_list():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            birth_date,
            personality
        FROM dogs
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    dogs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dog/dog_list.html",
        dogs=dogs
    )

@app.route("/dog/edit/<int:dog_id>", methods=["GET", "POST"])
def dog_edit(dog_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 현재 로그인한 사용자의 반려견인지 확인
    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            birth_date,
            personality
        FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    dog = cursor.fetchone()

    if not dog:
        cursor.close()
        conn.close()
        return "반려견을 찾을 수 없습니다.", 404

    # 수정 화면
    if request.method == "GET":
        cursor.close()
        conn.close()

        return render_template(
            "dog/dog_edit.html",
            dog=dog
        )

    # 수정된 값 받기
    name = request.form.get("name")
    breed = request.form.get("breed")
    size_category = request.form.get("size_category")
    birth_date = request.form.get("birth_date")
    personality = request.form.get("personality")

    cursor.execute("""
        UPDATE dogs
        SET
            name = %s,
            breed = %s,
            size_category = %s,
            birth_date = %s,
            personality = %s
        WHERE id = %s
          AND user_id = %s
    """, (
        name,
        breed,
        size_category,
        birth_date if birth_date else None,
        personality,
        dog_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dogs")

@app.route("/dog/delete/<int:dog_id>", methods=["POST"])
def dog_delete(dog_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # 현재 로그인한 사용자의 반려견만 삭제
    cursor.execute("""
        DELETE FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dogs")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)