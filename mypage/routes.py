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


        
        # ==============================
        # 메이트 신뢰도
        # ==============================

        cursor.execute("""
            SELECT
                punctuality_score,
                kindness_score,
                communication_score,
                dog_care_score
            FROM mate_reviews
            WHERE reviewed_user_id = %s
            ORDER BY id ASC
        """, (user_id,))

        reviews = cursor.fetchall()

        # 기존 평가까지 포함한 전체 평가 수
        review_count = len(reviews)

        base_score = 60
        review_change = 0

        for review in reviews:

            # 기존 방식으로 저장된 평가는
            # 세부 항목이 없으므로 계산에서 제외
            if any(
                review[field] is None
                for field in [
                    "punctuality_score",
                    "kindness_score",
                    "communication_score",
                    "dog_care_score"
                ]
            ):
                continue

            weighted_rating = (
                review["punctuality_score"] * 0.30
                + review["kindness_score"] * 0.25
                + review["communication_score"] * 0.20
                + review["dog_care_score"] * 0.25
            )

            if weighted_rating >= 4.5:
                review_change += 2

            elif weighted_rating >= 3.5:
                review_change += 1

            elif weighted_rating >= 2.5:
                review_change += 0

            elif weighted_rating >= 1.5:
                review_change -= 2

            else:
                review_change -= 3

        # ==============================
        # 확정된 노쇼 횟수
        # ==============================

        cursor.execute("""
            SELECT COUNT(*) AS no_show_count
            FROM mate_no_show_reports
            WHERE reported_user_id = %s
              AND status = 'confirmed'
        """, (user_id,))

        no_show_result = cursor.fetchone()
        no_show_count = no_show_result["no_show_count"] or 0

        # 노쇼 누적 감점
        if no_show_count == 0:
            no_show_penalty = 0
        elif no_show_count == 1:
            no_show_penalty = 3
        elif no_show_count == 2:
            no_show_penalty = 10
        else:
            # 3회부터 22점 감점
            no_show_penalty = 22

        # ==============================
        # 최종 신뢰도
        # ==============================

        trust_score = max(
            0,
            min(
                100,
                base_score + review_change - no_show_penalty
            )
        )



        # ==============================
        # 메이트 신청 응답률
        # ==============================

        cursor.execute("""
            SELECT
                COUNT(*) AS total_count,

                SUM(
                    CASE
                        WHEN mr.status IN (
                            '수락',
                            '거절'
                        )
                        THEN 1
                        ELSE 0
                    END
                ) AS responded_count

            FROM match_requests mr

            JOIN match_posts mp
                ON mr.match_post_id = mp.id

            WHERE mp.user_id = %s
        """, (user_id,))

        response_stats = cursor.fetchone()

        total_requests = (
            response_stats["total_count"] or 0
        )

        responded_requests = (
            response_stats["responded_count"] or 0
        )


        # 받은 신청이 있을 경우
        if total_requests > 0:

            response_rate = round(
                responded_requests
                / total_requests
                * 100
            )

        else:

            # 아직 받은 신청이 없는 경우
            response_rate = None


        # ==============================
        # 메이트 정보
        # ==============================

        mate_info = {
            "trust_score": trust_score,
            "review_count": review_count,
            "response_rate": response_rate,
            "total_requests": total_requests
        }


    finally:

        cursor.close()
        conn.close()


    return render_template(
        "profile/mypage.html",
        user=user,
        dogs=dogs,
        mate_info=mate_info
    )


# ==============================
# 프로필 수정
# ==============================

@profile_bp.route(
    "/mypage/edit",
    methods=["GET", "POST"]
)
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
            "nickname",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()


        if not nickname:
            return (
                "닉네임을 입력해주세요.",
                400
            )

        if not email:
            return (
                "이메일을 입력해주세요.",
                400
            )


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
            return (
                "이미 사용 중인 닉네임입니다.",
                400
            )


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
            return (
                "이미 사용 중인 이메일입니다.",
                400
            )


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

            if not allowed_image(
                image.filename
            ):

                return (
                    "PNG, JPG, JPEG, WEBP "
                    "이미지만 업로드할 수 있습니다.",
                    400
                )


            # 원래 확장자
            extension = (
                secure_filename(
                    image.filename
                )
                .rsplit(".", 1)[1]
                .lower()
            )


            # 파일명 충돌 방지를 위해 UUID 사용
            filename = (
                f"{uuid.uuid4().hex}."
                f"{extension}"
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


# ==============================
# 내가 작성한 장소 후기
# ==============================

@profile_bp.route("/mypage/reviews")
def my_reviews():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

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

    finally:

        cursor.close()
        conn.close()


    return render_template(
        "profile/my_reviews.html",
        reviews=reviews
    )