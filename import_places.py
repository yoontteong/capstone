from db import get_connection
from pet_tour_api import fetch_pet_places
from tour_api import fetch_tour_places


def guess_category(content_type_id):
    mapping = {
        "12": "관광지",
        "14": "문화시설",
        "28": "레포츠",
        "32": "숙소",
        "38": "쇼핑",
        "39": "맛집"
    }

    return mapping.get(str(content_type_id), "관광지")


def guess_stay_minutes(category):
    if category == "맛집":
        return 60

    elif category == "숙소":
        return 720

    elif category == "레포츠":
        return 120

    return 90


def insert_place(cursor, item, recommendation_type):
    name = item.get("title")
    address = item.get("addr1")
    latitude = item.get("mapy")
    longitude = item.get("mapx")
    content_type_id = item.get("contenttypeid")

    if not name or not latitude or not longitude:
        return False

    category = guess_category(content_type_id)
    stay_minutes = guess_stay_minutes(category)

    # 중복 체크
    cursor.execute(
        "SELECT id FROM places WHERE name = %s",
        (name,)
    )

    exists = cursor.fetchone()

    if exists:
        return False

    sql = """
        INSERT INTO places
        (
            name,
            category,
            address,
            latitude,
            longitude,
            dog_allowed,
            dog_size_allowed,
            indoor_outdoor,
            open_time,
            close_time,
            avg_stay_minutes,
            rating,
            recommendation_type
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            1,
            '전체',
            '정보없음',
            '09:00:00',
            '20:00:00',
            %s,
            4.0,
            %s
        )
    """

    cursor.execute(sql, (
        name,
        category,
        address,
        float(latitude),
        float(longitude),
        stay_minutes,
        recommendation_type
    ))

    return True


def insert_places():
    conn = get_connection()
    cursor = conn.cursor()

    total_count = 0

    print("\n=== 반려동물 API 데이터 저장 시작 ===")

    # 반려동물 API
    for page_no in range(1, 11):
        places = fetch_pet_places(
            num_of_rows=100,
            page_no=page_no
        )

        if not places:
            break

        for item in places:
            success = insert_place(
                cursor,
                item,
                "verified"
            )

            if success:
                total_count += 1

    print("\n=== 일반 관광 API 데이터 저장 시작 ===")

    # 일반 관광 API
    # 12 관광지
    # 14 문화시설
    # 28 레포츠

    content_types = [12, 14, 28, 32, 39]

    for content_type in content_types:

        for page_no in range(1, 11):

            places = fetch_tour_places(
                num_of_rows=100,
                page_no=page_no,
                content_type_id=content_type
            )

            if not places:
                break

            for item in places:
                success = insert_place(
                    cursor,
                    item,
                    "friendly"
                )

                if success:
                    total_count += 1

    conn.commit()

    cursor.close()
    conn.close()

    print(f"\n총 {total_count}개 장소 저장 완료")


if __name__ == "__main__":
    insert_places()