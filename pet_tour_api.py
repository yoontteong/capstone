import requests
from config import PET_API_KEY

BASE_URL = "https://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"

def fetch_pet_places(num_of_rows=100, page_no=1):
    params = {
        "serviceKey": PET_API_KEY,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "areaCode": 39,  # 제주도
        "MobileOS": "ETC",
        "MobileApp": "PinkSole",
        "_type": "json"
    }

    response = requests.get(BASE_URL, params=params, timeout=10)

    print("반려동물 API 요청 URL:")
    print(response.url)
    print("상태코드:", response.status_code)
    print("응답 앞부분:", response.text[:500])

    try:
        data = response.json()
    except Exception:
        print("반려동물 API JSON 변환 실패")
        return []

    body = data.get("response", {}).get("body", {})
    print("반려동물 API 전체 데이터 개수:", body.get("totalCount", 0))

    items_data = body.get("items", {})

    if not items_data or items_data == "":
        return []

    items = items_data.get("item", [])

    if isinstance(items, dict):
        items = [items]

    return items


if __name__ == "__main__":
    places = fetch_pet_places()
    print("가져온 개수:", len(places))

    for place in places[:5]:
        print(place.get("title"), place.get("addr1"))