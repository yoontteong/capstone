from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
from db import get_connection


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def get_days_by_period(travel_period):
    if travel_period == "1박2일":
        return 2
    elif travel_period == "2박3일":
        return 3
    return 1


def get_pattern_by_style(style):
    if style == "널널":
        return {
            "관광지": 2,
            "맛집": 2,
            "문화시설": 1
        }

    if style == "빡빡":
        return {
            "관광지": 4,
            "맛집": 2,
            "문화시설": 1,
            "레포츠": 1
        }

    return {
        "관광지": 3,
        "맛집": 2,
        "문화시설": 1
    }


def fetch_places(dog_size):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM places
        WHERE dog_allowed = 1
          AND (dog_size_allowed = %s OR dog_size_allowed = '전체')
        ORDER BY 
            CASE 
                WHEN recommendation_type = 'verified' THEN 0
                ELSE 1
            END,
            rating DESC
    """

    cursor.execute(sql, (dog_size,))
    places = cursor.fetchall()

    cursor.close()
    conn.close()

    return places


def select_places_by_pattern(places, pattern, used_place_ids):
    selected = []

    for category, count in pattern.items():
        verified_places = [
            place for place in places
            if place["category"] == category
            and place["recommendation_type"] == "verified"
            and place["id"] not in used_place_ids
        ]

        friendly_places = [
            place for place in places
            if place["category"] == category
            and place["recommendation_type"] == "friendly"
            and place["id"] not in used_place_ids
        ]

        verified_count = max(1, int(count * 0.5))
        friendly_count = count - verified_count

        selected.extend(verified_places[:verified_count])
        selected.extend(friendly_places[:friendly_count])

        if len(verified_places) < verified_count:
            shortage = verified_count - len(verified_places)
            selected.extend(friendly_places[friendly_count:friendly_count + shortage])

        if len(friendly_places) < friendly_count:
            shortage = friendly_count - len(friendly_places)
            selected.extend(verified_places[verified_count:verified_count + shortage])

    return selected


def sort_by_distance(places):
    if not places:
        return []

    route = [places[0]]
    remaining = places[1:]

    while remaining:
        current = route[-1]

        nearest = min(
            remaining,
            key=lambda place: calculate_distance(
                current["latitude"],
                current["longitude"],
                place["latitude"],
                place["longitude"]
            )
        )

        route.append(nearest)
        remaining.remove(nearest)

    return route


def is_place_open(place, current_time):
    try:
        open_time = datetime.strptime(str(place["open_time"]), "%H:%M:%S").time()
        close_time = datetime.strptime(str(place["close_time"]), "%H:%M:%S").time()
        now_time = current_time.time()

        return open_time <= now_time <= close_time
    except Exception:
        return True


def get_move_minutes_by_transport(transport_type):
    if transport_type == "뚜벅이":
        return 45
    elif transport_type == "대중교통":
        return 35
    elif transport_type == "자가용":
        return 20
    return 30


def create_day_schedule(route, day, transport_type):
    schedule = []

    current_time = datetime.strptime("10:00", "%H:%M")
    end_limit = datetime.strptime("20:00", "%H:%M")

    move_minutes = get_move_minutes_by_transport(transport_type)

    for place in route:
        if current_time >= end_limit:
            break

        if not is_place_open(place, current_time):
            continue

        stay_minutes = place["avg_stay_minutes"] or 90

        if stay_minutes >= 700:
            continue

        start_time = current_time
        finish_time = current_time + timedelta(minutes=stay_minutes)

        if finish_time > end_limit:
            break

        schedule.append({
            "day": day,
            "start_time": start_time.strftime("%H:%M"),
            "end_time": finish_time.strftime("%H:%M"),
            "place": place,
            "reason": make_reason(place)
        })

        current_time = finish_time + timedelta(minutes=move_minutes)

    return schedule


def make_reason(place):
    recommendation_type = place.get("recommendation_type", "verified")

    if recommendation_type == "verified":
        return (
            "공공 반려동물 동반여행 데이터에 등록된 검증 장소입니다. "
            "반려견과 함께 방문하기 적합한 장소로 우선 추천되었습니다."
        )

    return (
        "일반 관광 데이터를 기반으로 선택된 반려견 친화 추천 장소입니다. "
        "야외 활동이나 산책 중심 일정에 적합하며, 방문 전 동반 가능 여부 확인을 권장합니다."
    )


def generate_ai_schedule(dog_size, dog_personality, style, travel_period, transport_type):
    days = get_days_by_period(travel_period)
    pattern = get_pattern_by_style(style)

    places = fetch_places(dog_size)

    full_schedule = []
    used_place_ids = set()

    for day in range(1, days + 1):
        selected_places = select_places_by_pattern(
            places,
            pattern,
            used_place_ids
        )

        if not selected_places:
            continue

        for place in selected_places:
            used_place_ids.add(place["id"])

        route = sort_by_distance(selected_places)

        day_schedule = create_day_schedule(
            route,
            day,
            transport_type
        )

        full_schedule.extend(day_schedule)

    return full_schedule, pattern