from flask import render_template, request, redirect, url_for
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

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # -------------------------
    # 후기 작성 화면
    # -------------------------
    if request.method == "GET":

        cursor.execute("""
            SELECT
                id,
                name,
                category
            FROM places
            ORDER BY name ASC
        """)

        places = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "community/review_write.html",
            places=places
        )

    # -------------------------
    # 후기 저장
    # -------------------------
    place_id = request.form.get("place_id")

    author = request.form.get(
        "author",
        ""
    ).strip()

    rating = request.form.get("rating")

    content = request.form.get(
        "content",
        ""
    ).strip()

    if (
        not place_id
        or not author
        or not rating
        or not content
    ):
        cursor.close()
        conn.close()

        return (
            "모든 항목을 입력해주세요.",
            400
        )

    # 별점 검사
    try:
        rating = float(rating)

        if rating < 1 or rating > 5:
            raise ValueError

    except ValueError:

        cursor.close()
        conn.close()

        return (
            "별점은 1점에서 5점 사이여야 합니다.",
            400
        )

    # 후기 이미지 저장
    image_file = request.files.get("image")

    image_path = save_image(
        image_file
    )

    cursor.execute("""
        INSERT INTO reviews
        (
            place_id,
            author,
            rating,
            content,
            image_path
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        place_id,
        author,
        rating,
        content,
        image_path
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.review_list"
        )
    )