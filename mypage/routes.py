import os
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    current_app
)

from werkzeug.utils import secure_filename

from db import get_connection


profile_bp = Blueprint("profile", __name__)

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


# ==============================
# MY 페이지
# ==============================

@profile_bp.route("/mypage")
def mypage():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # ==============================
        # 사용자 정보 가져오기
        # ==============================
        cursor.execute("""
            SELECT
                id,
                username,
                nickname,
                email,
                profile_image,
                created_at
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cursor.fetchone()

        # 사용자가 존재하지 않는 경우
        if not user:
            session.clear()
            return redirect("/login")


        # ==============================
        # 사용자의 반려견 가져오기
        # ==============================
        cursor.execute("""
            SELECT
                id,
                name,
                breed,
                size_category,
                birth_date,
                personality
            FROM dogs
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,))

        dogs = cursor.fetchall()


    finally:
        cursor.close()
        conn.close()


    return render_template(
        "profile/mypage.html",
        user=user,
        dogs=dogs
    )


# ==============================
# 프로필 수정
# ==============================

@profile_bp.route("/mypage/edit", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ==============================
        # 프로필 수정 화면
        # ==============================

        if request.method == "GET":

            cursor.execute("""
                SELECT
                    id,
                    username,
                    nickname,
                    email,
                    profile_image
                FROM users
                WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                session.clear()
                return redirect("/login")

            return render_template(
                "profile/profile_edit.html",
                user=user
            )


        # ==============================
        # 기본 정보
        # ==============================

        nickname = request.form.get(
            "nickname", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()


        if not nickname:
            return "닉네임을 입력해주세요.", 400

        if not email:
            return "이메일을 입력해주세요.", 400


        # ==============================
        # 닉네임 중복 확인
        # ==============================

        cursor.execute("""
            SELECT id
            FROM users
            WHERE nickname = %s
              AND id != %s
        """, (
            nickname,
            user_id
        ))

        if cursor.fetchone():
            return "이미 사용 중인 닉네임입니다.", 400


        # ==============================
        # 이메일 중복 확인
        # ==============================

        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = %s
              AND id != %s
        """, (
            email,
            user_id
        ))

        if cursor.fetchone():
            return "이미 사용 중인 이메일입니다.", 400


        # ==============================
        # 현재 프로필 사진 가져오기
        # ==============================

        cursor.execute("""
            SELECT profile_image
            FROM users
            WHERE id = %s
        """, (user_id,))

        current_user = cursor.fetchone()

        profile_image = (
            current_user["profile_image"]
            if current_user
            else None
        )


        # ==============================
        # 새 프로필 사진
        # ==============================

        image = request.files.get(
            "profile_image"
        )


        if image and image.filename:

            if not allowed_image(image.filename):
                return (
                    "PNG, JPG, JPEG, WEBP "
                    "이미지만 업로드할 수 있습니다.",
                    400
                )


            # 원래 확장자
            extension = (
                secure_filename(image.filename)
                .rsplit(".", 1)[1]
                .lower()
            )


            # 파일명 충돌 방지를 위해 UUID 사용
            filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )


            upload_folder = os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                "profile"
            )


            # 폴더가 없어도 자동 생성
            os.makedirs(
                upload_folder,
                exist_ok=True
            )


            save_path = os.path.join(
                upload_folder,
                filename
            )


            image.save(save_path)


            # DB에는 실제 파일이 아니라
            # 브라우저에서 접근할 URL 저장
            profile_image = (
                f"/static/uploads/profile/"
                f"{filename}"
            )


        # ==============================
        # DB 수정
        # ==============================

        cursor.execute("""
            UPDATE users
            SET
                nickname = %s,
                email = %s,
                profile_image = %s
            WHERE id = %s
        """, (
            nickname,
            email,
            profile_image,
            user_id
        ))

        conn.commit()


        # 메인 화면 닉네임도 바로 변경
        session["nickname"] = nickname


    except Exception as e:

        conn.rollback()

        print(
            "프로필 수정 오류:",
            e
        )

        return (
            "프로필 수정 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect("/mypage")

# =========================
# 내가 작성한 장소 후기
# =========================
@profile_bp.route("/mypage/reviews")
def my_reviews():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

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
            r.updated_at,

            p.name AS place_name,
            p.category AS place_category,
            p.address AS place_address

        FROM reviews r

        JOIN places p
            ON r.place_id = p.id

        WHERE r.user_id = %s

        ORDER BY r.created_at DESC
    """, (
        user_id,
    ))

    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "profile/my_reviews.html",
        reviews=reviews
    )
    