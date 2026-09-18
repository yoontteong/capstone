from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session
)

from db import get_connection

from . import community
from .utils import save_image


# =========================
# 장소 후기 목록
# =========================
@community.route("/reviews")
def review_list():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            r.id,
            r.user_id,
            r.place_id,
            r.author,
            r.rating,
            r.content,
            r.image_path,
            r.created_at,
            p.name AS place_name
        FROM reviews r
        JOIN places p
            ON r.place_id = p.id
        ORDER BY r.id DESC
    """)

    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/reviews.html",
        reviews=reviews
    )


# =========================
# 장소 후기 작성
# =========================
@community.route(
    "/reviews/write",
    methods=["GET", "POST"]
)
def review_write():

    # 로그인 필수
    if "user_id" not in session:
        return redirect("/login")


    # =========================
    # GET
    # =========================
    if request.method == "GET":

        return render_template(
            "community/review_write.html"
        )


    # =========================
    # POST
    # =========================

    place_name = request.form.get(
        "place_name",
        ""
    ).strip()

    place_address = request.form.get(
        "place_address",
        ""
    ).strip()

    place_category = request.form.get(
        "place_category",
        ""
    ).strip()

    place_latitude = request.form.get(
        "place_latitude"
    )

    place_longitude = request.form.get(
        "place_longitude"
    )

    rating = request.form.get(
        "rating"
    )

    content = request.form.get(
        "content",
        ""
    ).strip()


    if (
        not place_name
        or not rating
        or not content
    ):
        return (
            "모든 필수 항목을 입력해주세요.",
            400
        )


    # =========================
    # 별점 검사
    # =========================

    try:

        rating = float(rating)

        if rating < 1 or rating > 5:
            raise ValueError

    except (ValueError, TypeError):

        return (
            "별점은 1점에서 5점 사이여야 합니다.",
            400
        )


    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # =========================
        # 사용자 닉네임
        # =========================

        cursor.execute("""
            SELECT nickname
            FROM users
            WHERE id = %s
        """, (
            session["user_id"],
        ))

        user = cursor.fetchone()


        if not user:
            return (
                "사용자 정보를 찾을 수 없습니다.",
                404
            )


        author = (
            user["nickname"]
            or "사용자"
        )


        # =========================
        # 기존 장소 확인
        # =========================

        cursor.execute("""
            SELECT id

            FROM places

            WHERE name = %s
              AND address = %s

            LIMIT 1
        """, (
            place_name,
            place_address
        ))

        place = cursor.fetchone()


        # =========================
        # 장소가 없으면 places 추가
        # =========================

        if place:

            place_id = place["id"]

        else:

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
                    recommendation_type
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                place_name,
                place_category or "기타",
                place_address,

                float(place_latitude)
                if place_latitude
                else None,

                float(place_longitude)
                if place_longitude
                else None,

                1,
                "전체",
                "정보없음",
                "custom"
            ))

            place_id = cursor.lastrowid


        # =========================
        # 이미지
        # =========================

        image_file = request.files.get(
            "image"
        )

        image_path = save_image(
            image_file
        )


        # =========================
        # 후기 저장
        # =========================

        cursor.execute("""
            INSERT INTO reviews
            (
                user_id,
                place_id,
                author,
                rating,
                content,
                image_path
            )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            session["user_id"],
            place_id,
            author,
            rating,
            content,
            image_path
        ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "장소 후기 저장 오류:",
            e
        )

        return (
            "후기 저장 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.review_list"
        )
    )