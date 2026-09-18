from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session
)

from db import get_connection
from activity.service import calculate_activity_summary

from . import community


# =========================================================
# 매칭 적합도 계산
# =========================================================
def calculate_match_score(
    host_dog_id,
    host_dog_size,
    host_dog_personality,
    applicant_dog_id,
    applicant_dog_size,
    applicant_dog_personality
):

    total_score = 0

    # -----------------------------------------------------
    # 1. 체급 궁합 - 30점
    # -----------------------------------------------------
    if host_dog_size == applicant_dog_size:
        size_score = 30
    else:
        size_score = 15

    total_score += size_score


    # -----------------------------------------------------
    # 2. 성향 궁합 - 30점
    # -----------------------------------------------------
    if host_dog_personality == applicant_dog_personality:
        personality_score = 30
    else:
        personality_score = 15

    total_score += personality_score


    # -----------------------------------------------------
    # 3. GPS 활동성 궁합 - 40점
    # -----------------------------------------------------
    activity_score = None
    host_activity = None
    applicant_activity = None

    if host_dog_id and applicant_dog_id:

        host_summary = calculate_activity_summary(
            host_dog_id
        )

        applicant_summary = calculate_activity_summary(
            applicant_dog_id
        )

        if (
            host_summary
            and applicant_summary
            and host_summary["activity_score"] is not None
            and applicant_summary["activity_score"] is not None
        ):

            host_activity = (
                host_summary["activity_score"]
            )

            applicant_activity = (
                applicant_summary["activity_score"]
            )

            activity_difference = abs(
                host_activity
                - applicant_activity
            )

            activity_compatibility = (
                100
                - activity_difference
            )

            activity_score = round(
                activity_compatibility * 0.4
            )

            total_score += activity_score

        else:

            # GPS 기록이 부족하면
            # 활동성은 중립 점수
            activity_score = 20

            total_score += activity_score

    else:

        activity_score = 20

        total_score += activity_score


    return {
        "total_score": round(total_score),

        "size_score": size_score,

        "personality_score":
            personality_score,

        "activity_score":
            activity_score,

        "host_activity":
            host_activity,

        "applicant_activity":
            applicant_activity
    }


# =========================================================
# 여행 메이트 목록
# =========================================================
@community.route("/matches")
def match_list():

    conn = get_connection()
    cursor = conn.cursor(
        dictionary=True
    )

    cursor.execute("""
        SELECT
            id,
            user_id,
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


# =========================================================
# 여행 메이트 모집글 작성
# =========================================================
@community.route(
    "/matches/write",
    methods=["GET", "POST"]
)
def match_write():

    if "user_id" not in session:
        return redirect("/login")


    # -----------------------------------------------------
    # GET
    # 내 반려견 목록 표시
    # -----------------------------------------------------
    if request.method == "GET":

        conn = get_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute("""
            SELECT
                id,
                name,
                breed,
                size_category,
                personality

            FROM dogs

            WHERE user_id = %s

            ORDER BY created_at DESC
        """, (
            session["user_id"],
        ))

        dogs = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "community/match_write.html",
            dogs=dogs
        )


    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------
    title = request.form.get(
        "title",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    travel_date = request.form.get(
        "travel_date",
        ""
    ).strip()

    region = request.form.get(
        "region",
        ""
    ).strip()

    dog_id = request.form.get(
        "dog_id"
    )

    max_people = request.form.get(
        "max_people",
        "2"
    )


    if (
        not title
        or not content
        or not travel_date
        or not region
        or not dog_id
    ):

        return (
            "모든 필수 항목을 입력해주세요.",
            400
        )


    # -----------------------------------------------------
    # 모집 인원 검사
    # -----------------------------------------------------
    try:

        max_people = int(
            max_people
        )

        if (
            max_people < 2
            or max_people > 10
        ):
            raise ValueError

    except ValueError:

        return (
            "모집 인원은 2~10명으로 입력해주세요.",
            400
        )


    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    try:

        # -------------------------------------------------
        # 현재 사용자의 반려견인지 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                name,
                size_category,
                personality

            FROM dogs

            WHERE id = %s
              AND user_id = %s
        """, (
            dog_id,
            session["user_id"]
        ))

        dog = cursor.fetchone()


        if not dog:

            return (
                "반려견 정보를 찾을 수 없습니다.",
                404
            )


        # -------------------------------------------------
        # 작성자 이름
        # -------------------------------------------------
        author = (
            session.get("nickname")
            or "사용자"
        )


        # -------------------------------------------------
        # 모집글 저장
        # -------------------------------------------------
        cursor.execute("""
            INSERT INTO match_posts
            (
                user_id,
                author,
                title,
                content,
                travel_date,
                region,
                dog_id,
                dog_name,
                dog_size,
                dog_personality,
                max_people,
                status
            )

            VALUES
            (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                '모집중'
            )
        """, (
            session["user_id"],
            author,
            title,
            content,
            travel_date,
            region,
            dog["id"],
            dog["name"],
            dog["size_category"],
            dog["personality"],
            max_people
        ))

        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "메이트 모집글 저장 오류:",
            e
        )

        return (
            "모집글 저장 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_list"
        )
    )


# =========================================================
# 여행 메이트 모집글 상세
# =========================================================
@community.route(
    "/matches/<int:match_id>"
)
def match_detail(match_id):

    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    # -----------------------------------------------------
    # 모집글 조회
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM match_posts
        WHERE id = %s
    """, (
        match_id,
    ))

    match = cursor.fetchone()


    if not match:

        cursor.close()
        conn.close()

        return (
            "모집글을 찾을 수 없습니다.",
            404
        )


    # -----------------------------------------------------
    # 현재 로그인 사용자가 글 작성자인지
    # -----------------------------------------------------
    is_owner = (
        session.get("user_id") is not None
        and
        match.get("user_id")
        == session.get("user_id")
    )


    # -----------------------------------------------------
    # 신청 목록 조회
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM match_requests

        WHERE match_post_id = %s

        ORDER BY id DESC
    """, (
        match_id,
    ))

    requests_list = (
        cursor.fetchall()
    )


    # -----------------------------------------------------
    # 매칭 점수 계산
    # -----------------------------------------------------
    for req in requests_list:

        match_result = calculate_match_score(
            match["dog_id"],
            match["dog_size"],
            match["dog_personality"],

            req["dog_id"],
            req["dog_size"],
            req["dog_personality"]
        )

        req["match_score"] = (
            match_result["total_score"]
        )

        req["size_score"] = (
            match_result["size_score"]
        )

        req["personality_score"] = (
            match_result[
                "personality_score"
            ]
        )

        req["activity_match_score"] = (
            match_result[
                "activity_score"
            ]
        )

        req["host_activity"] = (
            match_result[
                "host_activity"
            ]
        )

        req["applicant_activity"] = (
            match_result[
                "applicant_activity"
            ]
        )


    # -----------------------------------------------------
    # 현재 참여 인원
    # -----------------------------------------------------
    accepted_count = sum(
        1
        for req in requests_list
        if req["status"] == "수락"
    )

    # 모집자 본인 포함
    current_people = (
        accepted_count + 1
    )


    # -----------------------------------------------------
    # 로그인 사용자의 반려견
    # -----------------------------------------------------
    dogs = []

    if session.get("user_id"):

        cursor.execute("""
            SELECT
                id,
                name,
                breed,
                size_category,
                personality

            FROM dogs

            WHERE user_id = %s

            ORDER BY created_at DESC
        """, (
            session["user_id"],
        ))

        dogs = cursor.fetchall()


    # -----------------------------------------------------
    # 이미 이 글에 신청했는지
    # -----------------------------------------------------
    already_applied = False

    user_request = None

    if session.get("user_id"):

        cursor.execute("""
            SELECT
                id,
                status

            FROM match_requests

            WHERE match_post_id = %s
              AND user_id = %s

            LIMIT 1
        """, (
            match_id,
            session["user_id"]
        ))

        user_request = (
            cursor.fetchone()
        )

        already_applied = (
            user_request is not None
        )


    cursor.close()
    conn.close()


    return render_template(
        "community/match_detail.html",

        match=match,

        requests_list=requests_list,

        current_people=current_people,

        dogs=dogs,

        is_owner=is_owner,

        already_applied=already_applied,

        user_request=user_request
    )


# =========================================================
# 여행 메이트 신청
# =========================================================
@community.route(
    "/matches/<int:match_id>/apply",
    methods=["POST"]
)
def match_apply(match_id):

    if "user_id" not in session:

        return redirect(
            "/login"
        )


    dog_id = request.form.get(
        "dog_id"
    )

    message = request.form.get(
        "message",
        ""
    ).strip()


    if not dog_id:

        return (
            "반려견을 선택해주세요.",
            400
        )


    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    try:

        # -------------------------------------------------
        # 모집글 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                user_id,
                status

            FROM match_posts

            WHERE id = %s
        """, (
            match_id,
        ))

        match = cursor.fetchone()


        if not match:

            return (
                "모집글을 찾을 수 없습니다.",
                404
            )


        # -------------------------------------------------
        # 모집 종료 확인
        # -------------------------------------------------
        if match["status"] != "모집중":

            return (
                "현재 모집이 종료된 글입니다.",
                400
            )


        # -------------------------------------------------
        # 자기 글 신청 금지
        # -------------------------------------------------
        if (
            match["user_id"]
            == session["user_id"]
        ):

            return (
                "본인이 작성한 모집글에는 신청할 수 없습니다.",
                400
            )


        # -------------------------------------------------
        # 중복 신청 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT id

            FROM match_requests

            WHERE match_post_id = %s
              AND user_id = %s

            LIMIT 1
        """, (
            match_id,
            session["user_id"]
        ))

        existing_request = (
            cursor.fetchone()
        )


        if existing_request:

            return (
                "이미 이 모집글에 신청했습니다.",
                400
            )


        # -------------------------------------------------
        # 현재 사용자의 반려견 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                name,
                size_category,
                personality

            FROM dogs

            WHERE id = %s
              AND user_id = %s
        """, (
            dog_id,
            session["user_id"]
        ))

        dog = cursor.fetchone()


        if not dog:

            return (
                "반려견 정보를 찾을 수 없습니다.",
                404
            )


        # -------------------------------------------------
        # 신청자 이름
        # -------------------------------------------------
        applicant = (
            session.get("nickname")
            or "사용자"
        )


        # -------------------------------------------------
        # 신청 저장
        # -------------------------------------------------
        cursor.execute("""
            INSERT INTO match_requests
            (
                match_post_id,
                user_id,
                applicant,
                dog_id,
                dog_name,
                dog_size,
                dog_personality,
                message,
                status
            )

            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                '대기중'
            )
        """, (
            match_id,
            session["user_id"],
            applicant,
            dog["id"],
            dog["name"],
            dog["size_category"],
            dog["personality"],
            message
        ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "매칭 신청 오류:",
            e
        )

        return (
            "매칭 신청 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )


# =========================================================
# 매칭 신청 수락
# =========================================================
@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/accept",
    methods=["POST"]
)
def match_request_accept(
    match_id,
    request_id
):

    if "user_id" not in session:

        return redirect(
            "/login"
        )


    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    try:

        # -------------------------------------------------
        # 모집글 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                user_id,
                max_people,
                status

            FROM match_posts

            WHERE id = %s
        """, (
            match_id,
        ))

        match = cursor.fetchone()


        if not match:

            return (
                "모집글을 찾을 수 없습니다.",
                404
            )


        # -------------------------------------------------
        # 모집자 본인만 처리 가능
        # -------------------------------------------------
        if (
            match["user_id"]
            != session["user_id"]
        ):

            return (
                "신청을 처리할 권한이 없습니다.",
                403
            )


        if match["status"] != "모집중":

            return (
                "이미 모집이 완료되었습니다.",
                400
            )


        # -------------------------------------------------
        # 신청 존재 여부 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                status

            FROM match_requests

            WHERE id = %s
              AND match_post_id = %s
        """, (
            request_id,
            match_id
        ))

        match_request = (
            cursor.fetchone()
        )


        if not match_request:

            return (
                "매칭 신청을 찾을 수 없습니다.",
                404
            )


        if (
            match_request["status"]
            != "대기중"
        ):

            return (
                "이미 처리된 신청입니다.",
                400
            )


        # -------------------------------------------------
        # 현재 수락 인원
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*) AS accepted_count

            FROM match_requests

            WHERE match_post_id = %s
              AND status = '수락'
        """, (
            match_id,
        ))

        result = cursor.fetchone()

        accepted_count = (
            result["accepted_count"]
        )

        # 모집자 본인 포함
        current_people = (
            accepted_count + 1
        )


        if (
            current_people
            >= match["max_people"]
        ):

            cursor.execute("""
                UPDATE match_posts

                SET status = '모집완료'

                WHERE id = %s
            """, (
                match_id,
            ))

            conn.commit()

            return redirect(
                url_for(
                    "community.match_detail",
                    match_id=match_id
                )
            )


        # -------------------------------------------------
        # 신청 수락
        # -------------------------------------------------
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


        # -------------------------------------------------
        # 수락 이후 다시 인원 계산
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*) AS accepted_count

            FROM match_requests

            WHERE match_post_id = %s
              AND status = '수락'
        """, (
            match_id,
        ))

        accepted_count = (
            cursor.fetchone()[
                "accepted_count"
            ]
        )

        current_people = (
            accepted_count + 1
        )


        # -------------------------------------------------
        # 정원이 찼으면 자동 모집 완료
        # -------------------------------------------------
        if (
            current_people
            >= match["max_people"]
        ):

            cursor.execute("""
                UPDATE match_posts

                SET status = '모집완료'

                WHERE id = %s
            """, (
                match_id,
            ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "매칭 신청 수락 오류:",
            e
        )

        return (
            "신청 처리 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )


# =========================================================
# 매칭 신청 거절
# =========================================================
@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/reject",
    methods=["POST"]
)
def match_request_reject(
    match_id,
    request_id
):

    if "user_id" not in session:

        return redirect(
            "/login"
        )


    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    try:

        # -------------------------------------------------
        # 모집글 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                user_id

            FROM match_posts

            WHERE id = %s
        """, (
            match_id,
        ))

        match = cursor.fetchone()


        if not match:

            return (
                "모집글을 찾을 수 없습니다.",
                404
            )


        # -------------------------------------------------
        # 작성자만 거절 가능
        # -------------------------------------------------
        if (
            match["user_id"]
            != session["user_id"]
        ):

            return (
                "신청을 처리할 권한이 없습니다.",
                403
            )


        # -------------------------------------------------
        # 신청 확인
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                status

            FROM match_requests

            WHERE id = %s
              AND match_post_id = %s
        """, (
            request_id,
            match_id
        ))

        match_request = (
            cursor.fetchone()
        )


        if not match_request:

            return (
                "매칭 신청을 찾을 수 없습니다.",
                404
            )


        if (
            match_request["status"]
            != "대기중"
        ):

            return (
                "이미 처리된 신청입니다.",
                400
            )


        # -------------------------------------------------
        # 거절
        # -------------------------------------------------
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


    except Exception as e:

        conn.rollback()

        print(
            "매칭 신청 거절 오류:",
            e
        )

        return (
            "신청 처리 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )

# =========================================================
# 여행 메이트 모집글 수정
# =========================================================
@community.route(
    "/matches/<int:match_id>/edit",
    methods=["GET", "POST"]
)
def match_edit(match_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # 현재 사용자의 글인지 확인
        cursor.execute("""
            SELECT *
            FROM match_posts
            WHERE id = %s
              AND user_id = %s
        """, (
            match_id,
            session["user_id"]
        ))

        match = cursor.fetchone()

        if not match:
            return (
                "수정할 권한이 없거나 모집글을 찾을 수 없습니다.",
                404
            )


        # GET → 수정 화면
        if request.method == "GET":

            return render_template(
                "community/match_edit.html",
                match=match
            )


        # POST → 수정 저장
        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        travel_date = request.form.get(
            "travel_date",
            ""
        ).strip()

        region = request.form.get(
            "region",
            ""
        ).strip()

        max_people = request.form.get(
            "max_people",
            "2"
        )


        if (
            not title
            or not content
            or not travel_date
            or not region
        ):
            return (
                "모든 필수 항목을 입력해주세요.",
                400
            )


        try:

            max_people = int(
                max_people
            )

            if (
                max_people < 2
                or max_people > 10
            ):
                raise ValueError

        except ValueError:

            return (
                "모집 인원은 2~10명으로 입력해주세요.",
                400
            )


        # 이미 수락한 인원보다 모집인원을 작게 설정하지 못하게
        cursor.execute("""
            SELECT
                COUNT(*) AS accepted_count
            FROM match_requests
            WHERE match_post_id = %s
              AND status = '수락'
        """, (
            match_id,
        ))

        accepted_count = (
            cursor.fetchone()[
                "accepted_count"
            ]
        )

        current_people = (
            accepted_count + 1
        )


        if max_people < current_people:

            return (
                f"현재 참여 인원이 {current_people}명이므로 "
                f"모집 인원을 그보다 작게 설정할 수 없습니다.",
                400
            )


        cursor.execute("""
            UPDATE match_posts
            SET
                title = %s,
                content = %s,
                travel_date = %s,
                region = %s,
                max_people = %s
            WHERE id = %s
              AND user_id = %s
        """, (
            title,
            content,
            travel_date,
            region,
            max_people,
            match_id,
            session["user_id"]
        ))


        # 인원에 여유가 생기면 모집중으로 복구
        if current_people < max_people:

            cursor.execute("""
                UPDATE match_posts
                SET status = '모집중'
                WHERE id = %s
            """, (
                match_id,
            ))

        else:

            cursor.execute("""
                UPDATE match_posts
                SET status = '모집완료'
                WHERE id = %s
            """, (
                match_id,
            ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "모집글 수정 오류:",
            e
        )

        return (
            "모집글 수정 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )


# =========================================================
# 여행 메이트 모집글 삭제
# =========================================================
@community.route(
    "/matches/<int:match_id>/delete",
    methods=["POST"]
)
def match_delete(match_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # 작성자 본인인지 확인
        cursor.execute("""
            SELECT id
            FROM match_posts
            WHERE id = %s
              AND user_id = %s
        """, (
            match_id,
            session["user_id"]
        ))

        match = cursor.fetchone()

        if not match:

            return (
                "삭제할 권한이 없거나 모집글을 찾을 수 없습니다.",
                404
            )


        # 연결된 매칭 신청 먼저 삭제
        cursor.execute("""
            DELETE FROM match_requests
            WHERE match_post_id = %s
        """, (
            match_id,
        ))


        # 모집글 삭제
        cursor.execute("""
            DELETE FROM match_posts
            WHERE id = %s
              AND user_id = %s
        """, (
            match_id,
            session["user_id"]
        ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "모집글 삭제 오류:",
            e
        )

        return (
            "모집글 삭제 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_list"
        )
    )

# =========================================================
# 여행 메이트 신청 취소
# =========================================================
@community.route(
    "/matches/<int:match_id>/cancel",
    methods=["POST"]
)
def match_request_cancel(match_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # 현재 사용자의 신청 확인
        cursor.execute("""
            SELECT
                id,
                status

            FROM match_requests

            WHERE match_post_id = %s
              AND user_id = %s

            LIMIT 1
        """, (
            match_id,
            session["user_id"]
        ))

        match_request = cursor.fetchone()


        if not match_request:

            return (
                "취소할 매칭 신청을 찾을 수 없습니다.",
                404
            )


        if match_request["status"] != "대기중":

            return (
                "대기 중인 신청만 취소할 수 있습니다.",
                400
            )


        cursor.execute("""
            DELETE FROM match_requests

            WHERE id = %s
              AND match_post_id = %s
              AND user_id = %s
              AND status = '대기중'
        """, (
            match_request["id"],
            match_id,
            session["user_id"]
        ))


        conn.commit()


    except Exception as e:

        conn.rollback()

        print(
            "매칭 신청 취소 오류:",
            e
        )

        return (
            "매칭 신청 취소 중 오류가 발생했습니다.",
            500
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for(
            "community.match_detail",
            match_id=match_id
        )
    )