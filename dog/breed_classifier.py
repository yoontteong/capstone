from transformers import pipeline
from PIL import Image


# =========================================================
# AI 모델 설정
# =========================================================

MODEL_NAME = (
    "amaye15/"
    "google-vit-base-patch16-224-batch32-lr5e-05-standford-dogs"
)


# 처음에는 모델을 불러오지 않음
classifier = None


def get_classifier():
    global classifier

    # 아직 모델이 로드되지 않았을 때만 실행
    if classifier is None:
        print("견종 분류 AI 모델을 불러오는 중...")

        classifier = pipeline(
            "image-classification",
            model=MODEL_NAME
        )

        print("AI 모델 로드 완료!")

    return classifier   


# =========================================================
# 견종 정보
#
# 키는 모두 소문자 + 공백 형태로 작성한다.
#
# 예)
# "Maltese Dog"      -> "maltese dog"
# "Toy Poodle"       -> "toy poodle"
# "Golden Retriever" -> "golden retriever"
#
# 값:
# (한글 견종명, 체급)
# =========================================================

BREED_INFO = {

    # =====================================================
    # 소형견
    # =====================================================

    "maltese dog":
        ("말티즈", "소형견"),

    "toy poodle":
        ("토이푸들", "소형견"),

    "miniature poodle":
        ("미니어처 푸들", "소형견"),

    "chihuahua":
        ("치와와", "소형견"),

    "pomeranian":
        ("포메라니안", "소형견"),

    "shih-tzu":
        ("시츄", "소형견"),

    "shih tzu":
        ("시츄", "소형견"),

    "yorkshire terrier":
        ("요크셔테리어", "소형견"),

    "papillon":
        ("파피용", "소형견"),

    "pug":
        ("퍼그", "소형견"),

    "japanese spaniel":
        ("재패니즈 친", "소형견"),

    "pekinese":
        ("페키니즈", "소형견"),

    "blenheim spaniel":
        ("카발리에 킹 찰스 스패니얼", "소형견"),

    "boston bull":
        ("보스턴 테리어", "소형견"),

    "miniature schnauzer":
        ("미니어처 슈나우저", "소형견"),

    "west highland white terrier":
        ("웨스트 하이랜드 화이트 테리어", "소형견"),

    "scottish terrier":
        ("스코티시 테리어", "소형견"),

    "norwich terrier":
        ("노리치 테리어", "소형견"),

    "norfolk terrier":
        ("노퍽 테리어", "소형견"),

    "dandie dinmont":
        ("댄디 딘몬트 테리어", "소형견"),

    "lhasa":
        ("라사압소", "소형견"),

    "tibetan terrier":
        ("티베탄 테리어", "소형견"),

    "australian terrier":
        ("오스트레일리안 테리어", "소형견"),

    "cairn":
        ("케언 테리어", "소형견"),

    "affenpinscher":
        ("아펜핀셔", "소형견"),

    "silky terrier":
        ("실키 테리어", "소형견"),

    "sealyham terrier":
        ("실리햄 테리어", "소형견"),

    "bedlington terrier":
    ("베들링턴 테리어", "소형견"),

    "border terrier":
        ("보더 테리어", "소형견"),

    "brabancon griffon":
        ("브뤼셀 그리펀", "소형견"),

    "italian greyhound":
        ("이탈리안 그레이하운드", "소형견"),

    "lakeland terrier":
        ("레이크랜드 테리어", "소형견"),

    "mexican hairless":
        ("멕시칸 헤어리스", "소형견"),

    "miniature pinscher":
        ("미니어처 핀셔", "소형견"),

    "toy terrier":
        ("토이 테리어", "소형견"),

    "wire haired fox terrier":
        ("와이어 폭스 테리어", "소형견"),
        


    # =====================================================
    # 중형견
    # =====================================================

    "beagle":
        ("비글", "중형견"),

    "border collie":
        ("보더콜리", "중형견"),

    "cocker spaniel":
        ("코커스패니얼", "중형견"),

    "english springer":
        ("잉글리시 스프링어 스패니얼", "중형견"),

    "welsh springer spaniel":
        ("웰시 스프링어 스패니얼", "중형견"),

    "french bulldog":
        ("프렌치 불도그", "중형견"),

    "pembroke":
        ("웰시코기 펨브로크", "중형견"),

    "cardigan":
        ("웰시코기 카디건", "중형견"),

    "siberian husky":
        ("시베리안 허스키", "중형견"),

    "american staffordshire terrier":
        ("아메리칸 스태퍼드셔 테리어", "중형견"),

    "staffordshire bullterrier":
        ("스태퍼드셔 불 테리어", "중형견"),

    "bull terrier":
        ("불 테리어", "중형견"),

    "basset":
        ("바셋 하운드", "중형견"),

    "whippet":
        ("휘핏", "중형견"),

    "brittany spaniel":
        ("브리타니 스패니얼", "중형견"),

    "irish terrier":
        ("아이리시 테리어", "중형견"),

    "kerry blue terrier":
        ("케리 블루 테리어", "중형견"),

    "soft-coated wheaten terrier":
        ("소프트 코티드 휘튼 테리어", "중형견"),

    "standard schnauzer":
        ("스탠더드 슈나우저", "중형견"),

    "english setter":
        ("잉글리시 세터", "중형견"),

    "irish setter":
        ("아이리시 세터", "중형견"),

    "gordon setter":
        ("고든 세터", "중형견"),

    "vizsla":
        ("비즐라", "중형견"),

    "basenji":
        ("바센지", "중형견"),

    "shiba inu":
        ("시바 이누", "중형견"),

    "chow":
        ("차우차우", "중형견"),

    "samoyed":
        ("사모예드", "중형견"),

    "keeshond":
        ("키스혼드", "중형견"),

    "norwegian elkhound":
        ("노르웨이 엘크하운드", "중형견"),

    "ibizan hound":
        ("이비전 하운드", "중형견"),

    "walker hound":
        ("트리잉 워커 쿤하운드", "중형견"),

    "english foxhound":
        ("잉글리시 폭스하운드", "중형견"),

    "bluetick":
        ("블루틱 쿤하운드", "중형견"),

    "redbone":
        ("레드본 쿤하운드", "중형견"),

    "afghan hound":
        ("아프간 하운드", "중형견"),

    "saluki":
        ("살루키", "중형견"),

    "borzoi":
        ("보르조이", "중형견"),

    "dalmatian":
        ("달마시안", "중형견"),

    "boxer":
        ("복서", "중형견"),

    "airedale":
        ("에어데일 테리어", "중형견"),

    "schipperke":
        ("스키퍼키", "중형견"),

    "collie":
        ("콜리", "중형견"),

    "shetland sheepdog":
        ("셔틀랜드 쉽독", "중형견"),

    "australian shepherd":
        ("오스트레일리안 셰퍼드", "중형견"),

    "african hunting dog":
    ("아프리카들개", "중형견"),

    "black and tan coonhound":
        ("블랙 앤 탄 쿤하운드", "중형견"),

    "clumber":
        ("클럼버 스패니얼", "중형견"),

    "dhole":
        ("승냥이", "중형견"),

    "dingo":
        ("딩고", "중형견"),

    "eskimo dog":
        ("에스키모 도그", "중형견"),

    "german short haired pointer":
        ("저먼 쇼트헤어드 포인터", "중형견"),

    "irish water spaniel":
        ("아이리시 워터 스패니얼", "중형견"),

    "kelpie":
        ("오스트레일리안 켈피", "중형견"),

    "otterhound":
        ("오터하운드", "중형견"),

    "standard poodle":
        ("스탠더드 푸들", "중형견"),

    "sussex spaniel":
        ("서식스 스패니얼", "중형견"),    


    # =====================================================
    # 대형견
    # =====================================================

    "golden retriever":
        ("골든 리트리버", "대형견"),

    "labrador retriever":
        ("래브라도 리트리버", "대형견"),

    "german shepherd":
        ("저먼 셰퍼드", "대형견"),

    "german shepherd dog":
        ("저먼 셰퍼드", "대형견"),

    "rottweiler":
        ("로트와일러", "대형견"),

    "doberman":
        ("도베르만", "대형견"),

    "great dane":
        ("그레이트 데인", "대형견"),

    "saint bernard":
        ("세인트 버나드", "대형견"),

    "st bernard":
        ("세인트 버나드", "대형견"),

    "bernese mountain dog":
        ("버니즈 마운틴 도그", "대형견"),

    "newfoundland":
        ("뉴펀들랜드", "대형견"),

    "great pyrenees":
        ("그레이트 피레니즈", "대형견"),

    "mastiff":
        ("마스티프", "대형견"),

    "bull mastiff":
        ("불마스티프", "대형견"),

    "tibetan mastiff":
        ("티베탄 마스티프", "대형견"),

    "leonberg":
        ("레온베르거", "대형견"),

    "irish wolfhound":
        ("아이리시 울프하운드", "대형견"),

    "scottish deerhound":
        ("스코티시 디어하운드", "대형견"),

    "bloodhound":
        ("블러드하운드", "대형견"),

    "weimaraner":
        ("와이마라너", "대형견"),

    "rhodesian ridgeback":
        ("로디지안 리지백", "대형견"),

    "chesapeake bay retriever":
        ("체서피크 베이 리트리버", "대형견"),

    "flat-coated retriever":
        ("플랫 코티드 리트리버", "대형견"),

    "curly-coated retriever":
        ("컬리 코티드 리트리버", "대형견"),

    "old english sheepdog":
        ("올드 잉글리시 쉽독", "대형견"),

    "bouvier des flandres":
        ("부비에 데 플랑드르", "대형견"),

    "komondor":
        ("코몬도르", "대형견"),

    "kuvasz":
        ("쿠바스", "대형견"),

    "malinois":
        ("벨지안 말리노이즈", "대형견"),

    "groenendael":
        ("벨지안 쉽독", "대형견"),

    "briard":
        ("브리아드", "대형견"),

    "giant schnauzer":
        ("자이언트 슈나우저", "대형견"),

    "greater swiss mountain dog":
        ("그레이터 스위스 마운틴 도그", "대형견"),

    "entlebucher":
        ("엔틀레부허 마운틴 도그", "대형견"),

    "appenzeller":
        ("아펜첼러 세넨훈드", "대형견"),

    "alaskan malamute":
        ("알래스칸 말라뮤트", "대형견"),

    # =========================
    # 실제 라벨 이름 불일치 보완
    # =========================

    "scotch terrier":
        ("스코티시 테리어", "소형견"),

    "malamute":
        ("알래스칸 말라뮤트", "대형견"),    

}




# =========================================================
# AI 라벨 정규화
# =========================================================

def normalize_label(label):
    """
    모델에서 반환된 라벨을
    BREED_INFO와 비교하기 쉬운 형태로 변환한다.

    예:
    Maltese Dog      -> maltese dog
    Toy_Poodle       -> toy poodle
    Golden-Retriever -> golden retriever
    """

    normalized = label.strip().lower()

    normalized = normalized.replace(
        "_",
        " "
    )

    normalized = normalized.replace(
        "-",
        " "
    )

    # 연속된 공백 제거
    normalized = " ".join(
        normalized.split()
    )

    return normalized


# =========================================================
# 견종 정보 찾기
# =========================================================

def get_breed_info(label):

    normalized_label = normalize_label(
        label
    )


    # 정확히 일치하는 견종
    if normalized_label in BREED_INFO:

        return BREED_INFO[
            normalized_label
        ]


    # -----------------------------------------------------
    # 일부 모델 라벨에 "dog"가 붙는 경우 처리
    #
    # 예:
    # "Golden Retriever Dog"
    # -> "Golden Retriever"
    # -----------------------------------------------------

    if normalized_label.endswith(" dog"):

        without_dog = normalized_label[:-4]

        if without_dog in BREED_INFO:

            return BREED_INFO[
                without_dog
            ]


    # -----------------------------------------------------
    # 매핑되지 않은 견종
    #
    # 영어 원본은 그대로 보여주되
    # 보기 좋게 변환한다.
    # -----------------------------------------------------

    readable_name = label.replace(
        "_",
        " "
    )

    return readable_name, None


# =========================================================
# 견종 예측
# =========================================================

def predict_breed(image):

    """
    강아지 사진을 분석하여
    가능성이 높은 견종 TOP 3를 반환한다.
    """


    # -----------------------------------------------------
    # 이미지 불러오기
    # -----------------------------------------------------

    if isinstance(image, str):

        image = Image.open(
            image
        )


    elif not isinstance(
        image,
        Image.Image
    ):

        image = Image.open(
            image
        )


    # AI 입력 형식으로 변환
    image = image.convert(
        "RGB"
    )


    # -----------------------------------------------------
    # AI 견종 분석
    # -----------------------------------------------------

    model = get_classifier()

    predictions = model(
        image,
        top_k=3
    )


    results = []


    # -----------------------------------------------------
    # 결과 가공
    # -----------------------------------------------------

    for prediction in predictions:


        original_label = prediction[
            "label"
        ]


        # 개발 중 확인용
        print(
            "AI 원본 라벨:",
            original_label
        )


        korean_name, size_category = (
            get_breed_info(
                original_label
            )
        )


        results.append({

            # 사용자에게 보여줄 한글 견종명
            "breed":
                korean_name,

            # AI 모델의 원래 결과
            "original_breed":
                original_label,

            # 자동 체급
            "size_category":
                size_category,

            # AI 확률
            "confidence":
                round(
                    prediction["score"] * 100,
                    2
                )

        })


    return results


# =========================================================
# 단독 테스트
# =========================================================

if __name__ == "__main__":


    image_path = input(
        "강아지 사진 경로를 입력하세요: "
    ).strip()


    try:


        results = predict_breed(
            image_path
        )


        print(
            "\n===== 견종 분석 결과 ====="
        )


        for index, result in enumerate(
            results,
            start=1
        ):


            print(
                f"{index}위: "
                f"{result['breed']} "
                f"({result['confidence']}%) "
                f"- "
                f"{result['size_category'] or '체급 미등록'}"
            )


    except Exception as e:


        print(
            "\n견종 분석 중 오류가 발생했습니다."
        )


        print(e)