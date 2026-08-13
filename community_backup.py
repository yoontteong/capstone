from flask import Blueprint, render_template, request, redirect, url_for
from db import get_connection

import os
import uuid
from werkzeug.utils import secure_filename

community = Blueprint("community", __name__)

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_image(file):
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        return None

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()

    new_filename = f"{uuid.uuid4().hex}.{extension}"

    save_path = os.path.join(
        UPLOAD_FOLDER,
        new_filename
    )

    file.save(save_path)

    # DB에는 웹에서 접근할 수 있는 경로 저장
    return f"uploads/{new_filename}"


@community.route("/community")
def community_list():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, author, title, created_at
        FROM posts
        ORDER BY id DESC
    """)

    posts = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/community.html",
        posts=posts
    )

@community.route("/community/write", methods=["GET", "POST"])
def community_write():

    if request.method == "GET":
        return render_template("community/community_write.html")

    author = request.form.get("author", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not author or not title or not content:
        return "작성자, 제목, 내용을 모두 입력해주세요.", 400

    image_file = request.files.get("image")
    image_path = save_image(image_file)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts
        (
            author,
            title,
            content,
            image_path
        )
        VALUES (%s, %s, %s, %s)
    """, (
        author,
        title,
        content,
        image_path
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for("community.community_list")
    )

@community.route("/community/<int:post_id>")
def community_detail(post_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 게시글 조회
    cursor.execute("""
        SELECT id, author, title, content, image_path,
               created_at, updated_at
        FROM posts
        WHERE id = %s
    """, (post_id,))

    post = cursor.fetchone()

    if not post:
        cursor.close()
        conn.close()
        return "게시글을 찾을 수 없습니다.", 404

    # 해당 게시글의 댓글 조회
    cursor.execute("""
        SELECT id, post_id, author, content,
               created_at, updated_at
        FROM comments
        WHERE post_id = %s
        ORDER BY id ASC
    """, (post_id,))

    comments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/community_detail.html",
        post=post,
        comments=comments
    )

@community.route("/community/<int:post_id>/edit", methods=["GET", "POST"])
def community_edit(post_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 수정 화면 열기
    if request.method == "GET":
        cursor.execute("""
            SELECT id, author, title, content
            FROM posts
            WHERE id = %s
        """, (post_id,))

        post = cursor.fetchone()

        cursor.close()
        conn.close()

        if not post:
            return "게시글을 찾을 수 없습니다.", 404

        return render_template(
            "community/community_edit.html",
            post=post
        )

    # 수정 내용 저장
    author = request.form.get("author", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not author or not title or not content:
        cursor.close()
        conn.close()
        return "작성자, 제목, 내용을 모두 입력해주세요.", 400

    cursor.execute("""
        UPDATE posts
        SET author = %s,
            title = %s,
            content = %s
        WHERE id = %s
    """, (
        author,
        title,
        content,
        post_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

@community.route("/community/<int:post_id>/delete", methods=["POST"])
def community_delete(post_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM posts
        WHERE id = %s
    """, (post_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for("community.community_list")
    )

@community.route("/community/<int:post_id>/comments", methods=["POST"])
def comment_create(post_id):

    author = request.form.get("author", "").strip()
    content = request.form.get("content", "").strip()

    if not author or not content:
        return "작성자와 댓글 내용을 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comments
        (
            post_id,
            author,
            content
        )
        VALUES (%s, %s, %s)
    """, (
        post_id,
        author,
        content
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/edit",
    methods=["POST"]
)
def comment_edit(post_id, comment_id):

    content = request.form.get("content", "").strip()

    if not content:
        return "댓글 내용을 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE comments
        SET content = %s
        WHERE id = %s
          AND post_id = %s
    """, (
        content,
        comment_id,
        post_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/delete",
    methods=["POST"]
)
def comment_delete(post_id, comment_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM comments
        WHERE id = %s
          AND post_id = %s
    """, (
        comment_id,
        post_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

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
        JOIN places p ON r.place_id = p.id
        ORDER BY r.id DESC
    """)

    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/reviews.html",
        reviews=reviews
    )

@community.route("/reviews/write", methods=["GET", "POST"])
def review_write():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 후기 작성 화면
    if request.method == "GET":

        cursor.execute("""
            SELECT id, name, category
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

    # 작성된 후기 저장
    place_id = request.form.get("place_id")
    author = request.form.get("author", "").strip()
    rating = request.form.get("rating")
    content = request.form.get("content", "").strip()

    if not place_id or not author or not rating or not content:
        cursor.close()
        conn.close()
        return "모든 항목을 입력해주세요.", 400

    try:
        rating = float(rating)

        if rating < 1 or rating > 5:
            raise ValueError

    except ValueError:
        cursor.close()
        conn.close()
        return "별점은 1점에서 5점 사이여야 합니다.", 400

    # 기존 게시글에서 만든 이미지 저장 함수 재사용
    image_file = request.files.get("image")
    image_path = save_image(image_file)

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
        url_for("community.review_list")
    )

@community.route("/matches")
def match_list():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            author,
            title,
            content,
            travel_date,
            region,
            dog_name,
            dog_size,
            dog_personality,
            max_people,
            status,
            created_at
        FROM match_posts
        ORDER BY id DESC
    """)

    matches = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/matches.html",
        matches=matches
    )

@community.route("/matches/write", methods=["GET", "POST"])
def match_write():

    if request.method == "GET":
        return render_template("community/match_write.html")

    author = request.form.get("author", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    travel_date = request.form.get("travel_date", "").strip()
    region = request.form.get("region", "").strip()

    dog_name = request.form.get("dog_name", "").strip()
    dog_size = request.form.get("dog_size", "").strip()
    dog_personality = request.form.get("dog_personality", "").strip()

    max_people = request.form.get("max_people", "2")

    if (
        not author
        or not title
        or not content
        or not travel_date
        or not region
        or not dog_name
        or not dog_size
        or not dog_personality
    ):
        return "모든 필수 항목을 입력해주세요.", 400

    try:
        max_people = int(max_people)

        if max_people < 2 or max_people > 10:
            raise ValueError

    except ValueError:
        return "모집 인원은 2~10명으로 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO match_posts
        (
            author,
            title,
            content,
            travel_date,
            region,
            dog_name,
            dog_size,
            dog_personality,
            max_people,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '모집중')
    """, (
        author,
        title,
        content,
        travel_date,
        region,
        dog_name,
        dog_size,
        dog_personality,
        max_people
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for("community.match_list")
    )

@community.route("/matches/<int:match_id>")
def match_detail(match_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 조회
    cursor.execute("""
        SELECT *
        FROM match_posts
        WHERE id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        cursor.close()
        conn.close()
        return "모집글을 찾을 수 없습니다.", 404

    # 해당 모집글의 신청 목록 조회
    cursor.execute("""
        SELECT *
        FROM match_requests
        WHERE match_post_id = %s
        ORDER BY id DESC
    """, (match_id,))

    requests_list = cursor.fetchall()

    # 수락된 신청자 수 계산
    accepted_count = sum(
        1
        for req in requests_list
        if req["status"] == "수락"
    )

    # 모집글 작성자 본인도 1명으로 계산
    current_people = accepted_count + 1

    cursor.close()
    conn.close()

    return render_template(
        "community/match_detail.html",
        match=match,
        requests_list=requests_list,
        current_people=current_people
    )
@community.route(
    "/matches/<int:match_id>/apply",
    methods=["POST"]
)
def match_apply(match_id):

    applicant = request.form.get("applicant", "").strip()
    dog_name = request.form.get("dog_name", "").strip()
    dog_size = request.form.get("dog_size", "").strip()
    dog_personality = request.form.get("dog_personality", "").strip()
    message = request.form.get("message", "").strip()

    if (
        not applicant
        or not dog_name
        or not dog_size
        or not dog_personality
    ):
        return "필수 항목을 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 확인
    cursor.execute("""
        SELECT status
        FROM match_posts
        WHERE id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        cursor.close()
        conn.close()
        return "모집글을 찾을 수 없습니다.", 404

    if match["status"] != "모집중":
        cursor.close()
        conn.close()
        return "현재 모집이 종료된 글입니다.", 400

    # 신청 저장
    cursor.execute("""
        INSERT INTO match_requests
        (
            match_post_id,
            applicant,
            dog_name,
            dog_size,
            dog_personality,
            message,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, '대기중')
    """, (
        match_id,
        applicant,
        dog_name,
        dog_size,
        dog_personality,
        message
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )

@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/accept",
    methods=["POST"]
)
def match_request_accept(match_id, request_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 확인
    cursor.execute("""
        SELECT id, max_people, status
        FROM match_posts
        WHERE id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        cursor.close()
        conn.close()
        return "모집글을 찾을 수 없습니다.", 404

    if match["status"] != "모집중":
        cursor.close()
        conn.close()
        return "이미 모집이 완료되었습니다.", 400

    # 현재 수락된 신청자 수
    cursor.execute("""
        SELECT COUNT(*) AS accepted_count
        FROM match_requests
        WHERE match_post_id = %s
          AND status = '수락'
    """, (match_id,))

    result = cursor.fetchone()
    accepted_count = result["accepted_count"]

    # 작성자 본인도 1명으로 계산
    current_people = accepted_count + 1

    if current_people >= match["max_people"]:
        cursor.execute("""
            UPDATE match_posts
            SET status = '모집완료'
            WHERE id = %s
        """, (match_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(
            url_for(
                "community.match_detail",
                match_id=match_id
            )
        )

    # 신청 수락
    cursor.execute("""
        UPDATE match_requests
        SET status = '수락'
        WHERE id = %s
          AND match_post_id = %s
          AND status = '대기중'
    """, (
        request_id,
        match_id
    ))

    # 다시 수락 인원 계산
    cursor.execute("""
        SELECT COUNT(*) AS accepted_count
        FROM match_requests
        WHERE match_post_id = %s
          AND status = '수락'
    """, (match_id,))

    accepted_count = cursor.fetchone()["accepted_count"]

    # 작성자 포함
    current_people = accepted_count + 1

    # 모집 인원이 다 찼다면 자동 모집완료
    if current_people >= match["max_people"]:

        cursor.execute("""
            UPDATE match_posts
            SET status = '모집완료'
            WHERE id = %s
        """, (match_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )

@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/reject",
    methods=["POST"]
)
def match_request_reject(match_id, request_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE match_requests
        SET status = '거절'
        WHERE id = %s
          AND match_post_id = %s
          AND status = '대기중'
    """, (
        request_id,
        match_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )