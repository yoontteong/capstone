from db import get_connection

def calculate_activity_summary(dog_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 반려견 정보
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
    """, (dog_id,))

    dog = cursor.fetchone()

    if not dog:
        cursor.close()
        conn.close()
        return None


    # 최근 활동 기록 최대 10개
    cursor.execute("""
        SELECT
            distance_km,
            duration_seconds,
            average_speed,
            activity_date
        FROM activity_records
        WHERE dog_id = %s
        ORDER BY activity_date DESC
        LIMIT 10
    """, (dog_id,))

    records = cursor.fetchall()

    cursor.close()
    conn.close()


    record_count = len(records)


    # 기록이 하나도 없을 때
    if record_count == 0:

        return {
            "dog": dog,

            "record_count": 0,

            "avg_distance": 0,
            "avg_duration_minutes": 0,
            "avg_speed": 0,

            "activity_score": None,
            "activity_level": "기록 부족",

            "confidence": 0
        }


    # =========================
    # GPS 평균값 계산
    # =========================

    avg_distance = sum(
        float(record["distance_km"])
        for record in records
    ) / record_count


    avg_duration_minutes = sum(
        record["duration_seconds"]
        for record in records
    ) / record_count / 60


    valid_speeds = [
        float(record["average_speed"])
        for record in records
        if record["average_speed"] is not None
    ]


    if valid_speeds:
        avg_speed = (
            sum(valid_speeds)
            / len(valid_speeds)
        )
    else:
        avg_speed = 0


    # =========================
    # 체급별 활동 기준
    #
    # 현재는 매칭용 프로토타입 기준.
    # 나중에 품종/나이 기준 추가 예정.
    # =========================
    size_baselines = {
        "소형견": {
            "distance": 2.0,
            "duration": 40
        },

        "중형견": {
            "distance": 3.0,
            "duration": 50
        },

        "대형견": {
            "distance": 4.0,
            "duration": 60
        }
    }


    baseline = size_baselines.get(
        dog["size_category"],
        {
            "distance": 3.0,
            "duration": 50
        }
    )


    # =========================
    # 거리 점수 최대 50
    # =========================

    distance_ratio = (
        avg_distance
        / baseline["distance"]
    )


    distance_score = min(
        distance_ratio,
        1.0
    ) * 50


    # =========================
    # 활동시간 점수 최대 50
    # =========================

    duration_ratio = (
        avg_duration_minutes
        / baseline["duration"]
    )


    duration_score = min(
        duration_ratio,
        1.0
    ) * 50


    activity_score = round(
        distance_score
        + duration_score
    )


    # =========================
    # 활동성 등급
    # =========================

    if activity_score >= 81:
        activity_level = "매우 높음"

    elif activity_score >= 61:
        activity_level = "높음"

    elif activity_score >= 41:
        activity_level = "보통"

    elif activity_score >= 21:
        activity_level = "낮음"

    else:
        activity_level = "매우 낮음"


    # =========================
    # 데이터 신뢰도
    #
    # 10회 기록 → 100%
    # =========================

    confidence = min(
        record_count * 10,
        100
    )


    return {
        "dog": dog,

        "record_count":
            record_count,

        "avg_distance":
            round(avg_distance, 2),

        "avg_duration_minutes":
            round(avg_duration_minutes),

        "avg_speed":
            round(avg_speed, 1),

        "activity_score":
            activity_score,

        "activity_level":
            activity_level,

        "confidence":
            confidence,

        "distance_score":
            round(distance_score),

        "duration_score":
            round(duration_score)
    }