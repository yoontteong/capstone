from db import get_connection
from pet_tour_api import fetch_pet_places

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

def insert_places():
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        INSERT INTO places
        (name, category, address, latitude, longitude, dog_allowed,
         dog_size_allowed, indoor_outdoor, open_time, close_time,
         avg_stay_minutes, rating)
        VALUES (%s, %s, %s, %s, %s, 1, '전체', '정보없음',
                '09:00:00', '20:00:00', %s, 4.0)
    """

    total_count = 0

    for page_no in range(1, 11):  # 1~10페이지, 최대 1000개 시도
        places = fetch_pet_places(num_of_rows=100, page_no=page_no)

        if not places:
            break

        for item in places:
            name = item.get("title")
            address = item.get("addr1")
            latitude = item.get("mapy")
            longitude = item.get("mapx")
            content_type_id = item.get("contenttypeid")

            if not name or not latitude or not longitude:
                continue

            category = guess_category(content_type_id)

            if category == "맛집":
                stay_minutes = 60
            elif category == "숙소":
                stay_minutes = 720
            else:
                stay_minutes = 90

            cursor.execute(sql, (
                name,
                category,
                address,
                float(latitude),
                float(longitude),
                stay_minutes
            ))

            total_count += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"총 {total_count}개 장소 저장 완료")

if __name__ == "__main__":
    insert_places()