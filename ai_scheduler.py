from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
from db import get_connection


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    두 장소 사이의 거리 계산
    단위: km
    """
    R = 6371

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def get_pattern_by_style(style):
    """
    2. 여행 패턴 생성
    """
    if style == "널널":
        return {
            "카페": 2,
            "관광지": 1,
            "공원": 1,
            "맛집": 1
        }

    if style == "빡빡":
        return {
            "카페": 1,
            "관광지": 3,
            "공원": 1,
            "맛집": 1
        }

    return {
        "카페": 2,
        "관광지": 2,
        "공원": 1,
        "맛집": 1
    }


def fetch_places(dog_size):
    """
    3. 장소 추천 조건 적용
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM places
        WHERE dog_allowed = 1
          AND (dog_size_allowed = %s OR dog_size_allowed = '전체')
        ORDER BY rating DESC
    """

    cursor.execute(sql, (dog_size,))
    places = cursor.fetchall()

    cursor.close()
    conn.close()

    return places


def select_places_by_pattern(places, pattern):
    """
    일정 스타일에 맞게 카테고리별 장소 선택
    """
    selected = []

    for category, count in pattern.items():
        category_places = [
            place for place in places
            if place["category"] == category
        ]

        selected.extend(category_places[:count])

    return selected


def sort_by_distance(places):
    """
    4~5. 거리 기반 필터링 + 동선 생성
    가까운 장소 순서로 정렬
    """
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
    """
    7. 영업시간 고려
    """
    open_time = datetime.strptime(str(place["open_time"]), "%H:%M:%S").time()
    close_time = datetime.strptime(str(place["close_time"]), "%H:%M:%S").time()

    now_time = current_time.time()

    return open_time <= now_time <= close_time


def create_schedule(route):
    """
    6~7. 시간 순서 기반 일정 생성
    체류시간, 이동시간, 종료시간 제한 반영
    """
    schedule = []

    current_time = datetime.strptime("10:00", "%H:%M")
    end_limit = datetime.strptime("20:00", "%H:%M")

    for index, place in enumerate(route):
        if current_time >= end_limit:
            break

        if not is_place_open(place, current_time):
            continue

        stay_minutes = place["avg_stay_minutes"] or 60

        start_time = current_time
        finish_time = current_time + timedelta(minutes=stay_minutes)

        if finish_time > end_limit:
            break

        schedule.append({
            "start_time": start_time.strftime("%H:%M"),
            "end_time": finish_time.strftime("%H:%M"),
            "place": place,
            "reason": make_reason(place)
        })

        # 이동시간 30분 반영
        current_time = finish_time + timedelta(minutes=30)

    return schedule


def make_reason(place):
    """
    추천 이유 생성
    """
    return f"{place['category']} 장소이며, 반려견 동반이 가능하고 평점이 {place['rating']}점으로 높아 추천되었습니다."


def generate_ai_schedule(dog_size, dog_personality, style):
    """
    전체 AI 일정 생성 흐름
    1. 사용자 입력
    2. 여행 패턴 생성
    3. 장소 추천
    4. 거리 기반 필터링
    5. 동선 생성
    6. 일정 생성
    7. 영업시간/체류시간/종료시간 고려
    """
    pattern = get_pattern_by_style(style)
    places = fetch_places(dog_size)
    selected_places = select_places_by_pattern(places, pattern)
    route = sort_by_distance(selected_places)
    schedule = create_schedule(route)

    return schedule, pattern