import requests
from config import SERVICE_KEY

BASE_URL = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"

def fetch_pet_places(num_of_rows=100, page_no=1):
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "areaCode": 1,  # 서울
        "MobileOS": "ETC",
        "MobileApp": "PinkSole",
        "_type": "json"
    }

    response = requests.get(BASE_URL, params=params, timeout=10)

    print("요청 URL:")
    print(response.url)
    print("\n상태코드:")
    print(response.status_code)
    print("\n응답 앞부분:")
    print(response.text[:1000])

    try:
        data = response.json()
    except Exception:
        print("JSON 변환 실패")
        return []

    body = data.get("response", {}).get("body", {})

    total_count = body.get("totalCount", 0)
    print(f"\n전체 데이터 개수: {total_count}")

    items_data = body.get("items", {})

    # 2페이지처럼 items가 ""로 오는 경우 처리
    if not items_data or items_data == "":
        return []

    items = items_data.get("item", [])

    if isinstance(items, dict):
        items = [items]

    return items


if __name__ == "__main__":
    places = fetch_pet_places()
    print("가져온 개수:", len(places))

    for place in places[:3]:
        print(place["title"], place.get("addr1"))