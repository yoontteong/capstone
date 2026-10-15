
from flask import (
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

from db import get_connection
from . import community


# ==========================================
# 채팅방 접근 권한 확인
# ==========================================

def get_chat_permission(cursor, match_id, user_id):

    cursor.execute("""
        SELECT
            id,
            user_id,
            title,
            travel_date,
            status
        FROM match_posts
        WHERE id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        return None, False

    # 모집글 작성자는 입장 가능
    if match["user_id"] == user_id:
        return match, True

    # 수락된 신청자만 입장 가능
    cursor.execute("""
        SELECT id
        FROM match_requests
        WHERE match_post_id = %s
          AND user_id = %s
          AND status = '수락'
        LIMIT 1
    """, (match_id, user_id))

    accepted_request = cursor.fetchone()

    return match, accepted_request is not None


# ==========================================
# 단체 채팅방 화면
# ==========================================

@community.route("/matches/<int:match_id>/chat")
def mate_chat(match_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        match, allowed = get_chat_permission(
            cursor, match_id, user_id
        )

        if not match:
            return "모집글을 찾을 수 없습니다.", 404

        if not allowed:
            return "채팅방에 접근할 권한이 없습니다.", 403

        # 채팅방 참여자 목록
        cursor.execute("""
            SELECT
                u.id,
                COALESCE(u.nickname, u.username) AS nickname
            FROM users u
            WHERE u.id = %s

            UNION

            SELECT
                u.id,
                COALESCE(u.nickname, u.username) AS nickname
            FROM match_requests mr
            JOIN users u ON mr.user_id = u.id
            WHERE mr.match_post_id = %s
              AND mr.status = '수락'
        """, (match["user_id"], match_id))

        participants = cursor.fetchall()

        return render_template(
            "community/mate_chat.html",
            match=match,
            participants=participants,
            current_user_id=user_id
        )

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 채팅 메시지 조회 API
# ==========================================

@community.route(
    "/matches/<int:match_id>/chat/messages",
    methods=["GET"]
)
def mate_chat_messages(match_id):

    if "user_id" not in session:
        return jsonify({
            "error": "로그인이 필요합니다."
        }), 401

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        match, allowed = get_chat_permission(
            cursor, match_id, user_id
        )

        if not match:
            return jsonify({
                "error": "모집글을 찾을 수 없습니다."
            }), 404

        if not allowed:
            return jsonify({
                "error": "접근 권한이 없습니다."
            }), 403

        # 마지막으로 받은 메시지 ID 이후 조회
        try:
            after_id = max(
                0,
                int(request.args.get("after_id", 0))
            )
        except (ValueError, TypeError):
            return jsonify({
                "error": "잘못된 메시지 ID입니다."
            }), 400

        
        cursor.execute("""
            SELECT
                m.id,
                m.sender_id,
                COALESCE(
                    u.nickname,
                    u.username
                ) AS sender_name,
                m.message,
                m.created_at
            FROM mate_chat_messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.match_post_id = %s
              AND m.id > %s
            ORDER BY m.id ASC
            LIMIT 100
        """, (match_id, after_id))

        messages = cursor.fetchall()

        for message in messages:
            if message["created_at"]:
                message["created_at"] = (
                    message["created_at"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )


        return jsonify({
            "messages": messages,
            "current_user_id": user_id
        })

    finally:
        cursor.close()
        conn.close()



# ==========================================
# 채팅 메시지 전송 API
# ==========================================

@community.route(
    "/matches/<int:match_id>/chat/messages",
    methods=["POST"]
)
def mate_chat_send(match_id):

    if "user_id" not in session:
        return jsonify({
            "error": "로그인이 필요합니다."
        }), 401

    user_id = session["user_id"]

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message") or ""
    ).strip()

    if not message:
        return jsonify({
            "error": "메시지를 입력해주세요."
        }), 400

    if len(message) > 1000:
        return jsonify({
            "error": "메시지는 1000자 이하로 입력해주세요."
        }), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        match, allowed = get_chat_permission(
            cursor, match_id, user_id
        )

        if not match:
            return jsonify({
                "error": "모집글을 찾을 수 없습니다."
            }), 404

        if not allowed:
            return jsonify({
                "error": "메시지 전송 권한이 없습니다."
            }), 403

        cursor.execute("""
            INSERT INTO mate_chat_messages (
                match_post_id,
                sender_id,
                message
            )
            VALUES (%s, %s, %s)
        """, (
            match_id,
            user_id,
            message
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message_id": cursor.lastrowid
        }), 201
    except Exception:
        conn.rollback()
        raise


# ==========================================
# 내가 참여한 메이트 채팅방 목록
# ==========================================

@community.route("/matches/chats")
def mate_chat_list():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                mp.id,
                mp.title,
                mp.travel_date,

                (
                    SELECT COUNT(*)
                    FROM match_requests mr
                    WHERE mr.match_post_id = mp.id
                      AND mr.status = '수락'
                ) + 1 AS participant_count,

                (
                    SELECT m.message
                    FROM mate_chat_messages m
                    WHERE m.match_post_id = mp.id
                    ORDER BY m.id DESC
                    LIMIT 1
                ) AS last_message,

                (
                    SELECT m.created_at
                    FROM mate_chat_messages m
                    WHERE m.match_post_id = mp.id
                    ORDER BY m.id DESC
                    LIMIT 1
                ) AS last_message_at

            FROM match_posts mp

            WHERE mp.user_id = %s

               OR EXISTS (
                    SELECT 1
                    FROM match_requests mr
                    WHERE mr.match_post_id = mp.id
                      AND mr.user_id = %s
                      AND mr.status = '수락'
               )

            ORDER BY
                (last_message_at IS NULL) ASC,
                last_message_at DESC,
                mp.id DESC
        """, (user_id, user_id))

        chat_rooms = cursor.fetchall()

        return render_template(
            "community/mate_chat_list.html",
            chat_rooms=chat_rooms
        )

    finally:
        cursor.close()
        conn.close()
