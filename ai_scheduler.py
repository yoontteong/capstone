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
            "맛집": 2,
            "관광지": 2,
            "문화시설": 1
        }

    if style == "빡빡":
        return {
            "맛집": 3,
            "관광지": 4,
            "문화시설": 1,
            "레포츠": 1
        }

    return {
        "맛집": 3,
        "관광지": 3,
        "문화시설": 1
    }


def adjust_pattern_by_dog_size(pattern, dog_size):
    pattern = pattern.copy()

    if dog_size == "소형":
        pattern["문화시설"] = pattern.get("문화시설", 0) + 1
        pattern["맛집"] = pattern.get("맛집", 0) + 1

        if pattern.get("레포츠", 0) > 0:
            pattern["레포츠"] -= 1

    elif dog_size == "중형":
        pattern["관광지"] = pattern.get("관광지", 0) + 1

    elif dog_size == "대형":
        pattern["관광지"] = pattern.get("관광지", 0) + 1
        pattern["레포츠"] = pattern.get("레포츠", 0) + 1

        if pattern.get("문화시설", 0) > 0:
            pattern["문화시설"] -= 1

    return {k: v for k, v in pattern.items() if v > 0}


def adjust_pattern_by_dog_personality(pattern, dog_personality):
    pattern = pattern.copy()

    if dog_personality == "활발함":
        pattern["관광지"] = pattern.get("관광지", 0) + 1
        pattern["레포츠"] = pattern.get("레포츠", 0) + 1

    elif dog_personality == "조용함":
        pattern["문화시설"] = pattern.get("문화시설", 0) + 1
        pattern["맛집"] = pattern.get("맛집", 0) + 1

        if pattern.get("레포츠", 0) > 0:
            pattern["레포츠"] -= 1

    elif dog_personality == "겁많음":
        pattern["문화시설"] = pattern.get("문화시설", 0) + 1
        pattern["맛집"] = pattern.get("맛집", 0) + 1

        if pattern.get("레포츠", 0) > 0:
            pattern["레포츠"] -= 1

        if pattern.get("관광지", 0) > 1:
            pattern["관광지"] -= 1

    return {k: v for k, v in pattern.items() if v > 0}


def fetch_places(dog_size):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM places
        WHERE dog_allowed = 1
          AND category <> '숙소'
          AND (dog_size_allowed = %s OR dog_size_allowed = '전체')
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
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


def fetch_accommodations(dog_size):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM places
        WHERE category = '숙소'
          AND dog_allowed = 1
          AND (dog_size_allowed = %s OR dog_size_allowed = '전체')
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
        ORDER BY rating DESC
    """

    cursor.execute(sql, (dog_size,))
    accommodations = cursor.fetchall()

    cursor.close()
    conn.close()

    return accommodations


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


def get_region(place):
    address = place.get("address") or ""

    if "애월" in address:
        return "애월"
    elif "한림" in address or "협재" in address:
        return "한림/협재"
    elif "구좌" in address or "세화" in address or "월정" in address:
        return "구좌/월정"
    elif "성산" in address or "표선" in address:
        return "성산/표선"
    elif "조천" in address or "함덕" in address:
        return "조천/함덕"
    elif "서귀포시" in address:
        return "서귀포"
    elif "제주시" in address:
        return "제주시"

    return "기타"


def filter_by_region_cluster(places, transport_type):
    if not places:
        return []

    if transport_type != "뚜벅이":
        return places

    regions = {}

    for place in places:
        region = get_region(place)

        if region not in regions:
            regions[region] = []

        regions[region].append(place)

    best_region_places = max(
        regions.values(),
        key=len
    )

    return best_region_places


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


def find_nearest_accommodation(last_place, accommodations):
    if not last_place or not accommodations:
        return None

    if last_place.get("latitude") is None or last_place.get("longitude") is None:
        return None

    valid_accommodations = [
        acc for acc in accommodations
        if acc.get("latitude") is not None and acc.get("longitude") is not None
    ]

    if not valid_accommodations:
        return None

    return min(
        valid_accommodations,
        key=lambda acc: calculate_distance(
            last_place["latitude"],
            last_place["longitude"],
            acc["latitude"],
            acc["longitude"]
        )
    )


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


def create_day_schedule(route, day, transport_type, dog_size, dog_personality):
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
            "reason": make_reason(place, dog_size, dog_personality)
        })

        current_time = finish_time + timedelta(minutes=move_minutes)

    return schedule


def make_reason(place, dog_size=None, dog_personality=None):
    recommendation_type = place.get("recommendation_type", "verified")
    category = place.get("category", "")

    if category == "숙소":
        return "반려견 동반 가능 숙소이며, 여행 동선과 가까운 위치를 기준으로 추천되었습니다."

    size_reason = ""
    personality_reason = ""

    if dog_size == "소형":
        size_reason = "소형견과 함께 이동하기 부담이 적은 장소로 추천되었습니다. "
    elif dog_size == "중형":
        size_reason = "중형견의 활동량과 이동 부담을 고려하여 추천되었습니다. "
    elif dog_size == "대형":
        size_reason = "대형견이 비교적 넓게 활동할 수 있는 야외 중심 장소로 추천되었습니다. "

    if dog_personality == "활발함":
        personality_reason = "활동량이 많은 성향을 고려해 움직임이 있는 장소를 우선 반영했습니다. "
    elif dog_personality == "조용함":
        personality_reason = "조용한 성향을 고려해 부담이 적은 일정으로 구성했습니다. "
    elif dog_personality == "겁많음":
        personality_reason = "낯선 환경에 예민할 수 있어 비교적 안정적인 장소를 우선 반영했습니다. "

    if recommendation_type == "verified":
        return (
            size_reason +
            personality_reason +
            "공공 반려동물 동반여행 데이터에 등록된 검증 장소입니다."
        )

    return (
        size_reason +
        personality_reason +
        "일반 관광 데이터를 기반으로 선택된 반려견 친화 추천 장소입니다. "
        "방문 전 동반 가능 여부 확인을 권장합니다."
    )


def add_accommodation_to_schedule(full_schedule, accommodations, days, transport_type):
    if days <= 1:
        return full_schedule

    if not full_schedule or not accommodations:
        return full_schedule

    first_day_items = [
        item for item in full_schedule
        if item["day"] == 1 and item["place"]["category"] != "숙소"
    ]

    if not first_day_items:
        return full_schedule

    first_day_last_place = first_day_items[-1]["place"]

    accommodation = find_nearest_accommodation(
        first_day_last_place,
        accommodations
    )

    if not accommodation:
        return full_schedule

    move_minutes = get_move_minutes_by_transport(transport_type)

    for day in range(1, days):
        day_items = [
            item for item in full_schedule
            if item["day"] == day and item["place"]["category"] != "숙소"
        ]

        if not day_items:
            continue

        last_item = day_items[-1]

        try:
            start_time = datetime.strptime(last_item["end_time"], "%H:%M")
            start_time = start_time + timedelta(minutes=move_minutes)
            start_time_text = start_time.strftime("%H:%M")
        except Exception:
            start_time_text = ""

        full_schedule.append({
            "day": day,
            "start_time": start_time_text,
            "end_time": "",
            "place": accommodation,
            "reason": "여행 전체 동선을 고려해 선택된 반려견 동반 가능 숙소입니다."
        })

    full_schedule.sort(key=lambda x: (x["day"], x["start_time"] or "99:99"))

    return full_schedule


def generate_ai_schedule(dog_size, dog_personality, style, travel_period, transport_type):
    days = get_days_by_period(travel_period)

    pattern = get_pattern_by_style(style)
    pattern = adjust_pattern_by_dog_size(pattern, dog_size)
    pattern = adjust_pattern_by_dog_personality(pattern, dog_personality)

    places = fetch_places(dog_size)
    accommodations = fetch_accommodations(dog_size)

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

        selected_places = filter_by_region_cluster(
            selected_places,
            transport_type
        )

        if not selected_places:
            continue

        for place in selected_places:
            used_place_ids.add(place["id"])

        route = sort_by_distance(selected_places)

        day_schedule = create_day_schedule(
            route,
            day,
            transport_type,
            dog_size,
            dog_personality
        )

        full_schedule.extend(day_schedule)

    full_schedule = add_accommodation_to_schedule(
        full_schedule,
        accommodations,
        days,
        transport_type
    )

    return full_schedule, pattern