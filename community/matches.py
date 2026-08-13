from flask import render_template, request, redirect, url_for
from db import get_connection

from . import community


# =========================
# 여행 메이트 목록
# =========================
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


# =========================
# 여행 메이트 모집글 작성
# =========================
@community.route(
    "/matches/write",
    methods=["GET", "POST"]
)
def match_write():

    if request.method == "GET":
        return render_template(
            "community/match_write.html"
        )

    author = request.form.get(
        "author", ""
    ).strip()

    title = request.form.get(
        "title", ""
    ).strip()

    content = request.form.get(
        "content", ""
    ).strip()

    travel_date = request.form.get(
        "travel_date", ""
    ).strip()

    region = request.form.get(
        "region", ""
    ).strip()

    dog_name = request.form.get(
        "dog_name", ""
    ).strip()

    dog_size = request.form.get(
        "dog_size", ""
    ).strip()

    dog_personality = request.form.get(
        "dog_personality", ""
    ).strip()

    max_people = request.form.get(
        "max_people", "2"
    )

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
        return (
            "모든 필수 항목을 입력해주세요.",
            400
        )

    try:
        max_people = int(max_people)

        if max_people < 2 or max_people > 10:
            raise ValueError

    except ValueError:
        return (
            "모집 인원은 2~10명으로 입력해주세요.",
            400
        )

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
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, '모집중'
        )
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
        url_for(
            "community.match_list"
        )
    )


# =========================
# 여행 메이트 모집글 상세
# =========================
@community.route(
    "/matches/<int:match_id>"
)
def match_detail(match_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 조회
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

    # 해당 모집글의 신청 목록
    cursor.execute("""
        SELECT *
        FROM match_requests
        WHERE match_post_id = %s
        ORDER BY id DESC
    """, (
        match_id,
    ))

    requests_list = cursor.fetchall()

    # 수락된 신청자 수
    accepted_count = sum(
        1
        for req in requests_list
        if req["status"] == "수락"
    )

    # 작성자 본인 포함
    current_people = accepted_count + 1

    cursor.close()
    conn.close()

    return render_template(
        "community/match_detail.html",
        match=match,
        requests_list=requests_list,
        current_people=current_people
    )


# =========================
# 여행 메이트 신청
# =========================
@community.route(
    "/matches/<int:match_id>/apply",
    methods=["POST"]
)
def match_apply(match_id):

    applicant = request.form.get(
        "applicant", ""
    ).strip()

    dog_name = request.form.get(
        "dog_name", ""
    ).strip()

    dog_size = request.form.get(
        "dog_size", ""
    ).strip()

    dog_personality = request.form.get(
        "dog_personality", ""
    ).strip()

    message = request.form.get(
        "message", ""
    ).strip()

    if (
        not applicant
        or not dog_name
        or not dog_size
        or not dog_personality
    ):
        return (
            "필수 항목을 입력해주세요.",
            400
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 확인
    cursor.execute("""
        SELECT status
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

    if match["status"] != "모집중":
        cursor.close()
        conn.close()

        return (
            "현재 모집이 종료된 글입니다.",
            400
        )

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
        VALUES (
            %s, %s, %s, %s, %s, %s, '대기중'
        )
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


# =========================
# 매칭 신청 수락
# =========================
@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/accept",
    methods=["POST"]
)
def match_request_accept(
    match_id,
    request_id
):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 모집글 확인
    cursor.execute("""
        SELECT
            id,
            max_people,
            status
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

    if match["status"] != "모집중":
        cursor.close()
        conn.close()

        return (
            "이미 모집이 완료되었습니다.",
            400
        )

    # 현재 수락된 신청자 수
    cursor.execute("""
        SELECT COUNT(*) AS accepted_count
        FROM match_requests
        WHERE match_post_id = %s
          AND status = '수락'
    """, (
        match_id,
    ))

    result = cursor.fetchone()

    accepted_count = result[
        "accepted_count"
    ]

    # 작성자 포함
    current_people = accepted_count + 1

    # 이미 인원이 다 찬 경우
    if current_people >= match["max_people"]:

        cursor.execute("""
            UPDATE match_posts
            SET status = '모집완료'
            WHERE id = %s
        """, (
            match_id,
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

    # 수락 인원 다시 계산
    cursor.execute("""
        SELECT COUNT(*) AS accepted_count
        FROM match_requests
        WHERE match_post_id = %s
          AND status = '수락'
    """, (
        match_id,
    ))

    accepted_count = cursor.fetchone()[
        "accepted_count"
    ]

    current_people = accepted_count + 1

    # 인원이 다 찼으면 자동 모집완료
    if current_people >= match["max_people"]:

        cursor.execute("""
            UPDATE match_posts
            SET status = '모집완료'
            WHERE id = %s
        """, (
            match_id,
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


# =========================
# 매칭 신청 거절
# =========================
@community.route(
    "/matches/<int:match_id>/requests/<int:request_id>/reject",
    methods=["POST"]
)
def match_request_reject(
    match_id,
    request_id
):

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