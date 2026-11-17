from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort
)
from db import get_connection

from . import community
from .utils import save_image



# =========================
# 커뮤니티 메인
# =========================
@community.route("/community/home")
def community_home():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 최근 게시글 4개 조회
    cursor.execute("""
        SELECT id, author, title, created_at
        FROM posts
        ORDER BY id DESC
        LIMIT 4
    """)

    posts = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "community/community.html",
        posts=posts
    )


# =========================
# 자유게시판 목록
# =========================
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
        "community/community_board.html",
        posts=posts
    )



# =========================
# 게시글 작성
# =========================
@community.route("/community/write", methods=["GET", "POST"])
def community_write():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template(
            "community/community_write.html"
        )


    # =========================
    # 로그인 사용자 정보
    # =========================

    user_id = session["user_id"]
    author = session["nickname"]


    # =========================
    # 게시글 내용
    # =========================

    title = request.form.get(
        "title",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()


    if not title or not content:
        return (
            "제목과 내용을 모두 입력해주세요.",
            400
        )


    # =========================
    # 이미지 업로드
    # =========================

    image_file = request.files.get("image")

    image_path = save_image(
        image_file
    )


    # =========================
    # DB 저장
    # =========================

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts
        (
            user_id,
            author,
            title,
            content,
            image_path
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        user_id,
        author,
        title,
        content,
        image_path
    ))

    conn.commit()

    cursor.close()
    conn.close()


    return redirect(
        url_for(
            "community.community_list"
        )
    )

# =========================
# 게시글 상세
# =========================
@community.route(
    "/community/<int:post_id>"
)
def community_detail(post_id):

    conn = get_connection()
    cursor = conn.cursor(
        dictionary=True
    )

    # 게시글 조회
    cursor.execute("""
        SELECT
            id,
            user_id,
            author,
            title,
            content,
            image_path,
            created_at,
            updated_at
        FROM posts
        WHERE id = %s
    """, (
        post_id,
    ))

    post = cursor.fetchone()

    if not post:
        cursor.close()
        conn.close()

        return (
            "게시글을 찾을 수 없습니다.",
            404
        )

    # 댓글 조회
    cursor.execute("""
        SELECT
            id, post_id, user_id, author,
            content, created_at, updated_at
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


# =========================
# 게시글 수정
# =========================
@community.route(
    "/community/<int:post_id>/edit",
    methods=["GET", "POST"]
)
def community_edit(post_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, user_id, author, title, content
            FROM posts
            WHERE id = %s
        """, (post_id,))

        post = cursor.fetchone()

        if not post:
            abort(404)

        # 본인 글만 수정 가능
        if str(post["user_id"]) != str(session["user_id"]):
            abort(403)

        if request.method == "GET":
            return render_template(
                "community/community_edit.html",
                post=post
            )

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            return "제목과 내용을 모두 입력해주세요.", 400

        # 작성자명은 수정하지 않음
        cursor.execute("""
            UPDATE posts
            SET title = %s,
                content = %s
            WHERE id = %s AND user_id = %s
        """, (
            title,
            content,
            post_id,
            post["user_id"]
        ))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

# =========================
# 게시글 삭제
# =========================
@community.route(
    "/community/<int:post_id>/delete",
    methods=["POST"]
)
def community_delete(post_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id
            FROM posts
            WHERE id = %s
        """, (post_id,))

        post = cursor.fetchone()

        if not post:
            abort(404)

        is_author = (
            str(post["user_id"]) == str(session["user_id"])
        )

        is_admin = (
            session.get("role") == "admin"
        )

        if not (is_author or is_admin):
            abort(403)

        cursor.execute("""
            DELETE FROM posts
            WHERE id = %s
        """, (post_id,))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    return redirect(
        url_for("community.community_list")
    )

# =========================
# 댓글 작성
# =========================
@community.route(
    "/community/<int:post_id>/comments",
    methods=["POST"]
)
def comment_create(post_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    author = session["nickname"]

    content = request.form.get(
        "content", ""
    ).strip()

    if not content:
        return "댓글 내용을 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO comments
            (
                post_id,
                user_id,
                author,
                content
            )
            VALUES (%s, %s, %s, %s)
        """, (
            post_id,
            user_id,
            author,
            content
        ))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )

# =========================
# 댓글 수정
# =========================
@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/edit",
    methods=["POST"]
)
def comment_edit(post_id, comment_id):

    if "user_id" not in session:
        return redirect("/login")

    content = request.form.get(
        "content", ""
    ).strip()

    if not content:
        return "댓글 내용을 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id
            FROM comments
            WHERE id = %s
              AND post_id = %s
        """, (comment_id, post_id))

        comment = cursor.fetchone()

        if not comment:
            abort(404)

        if str(comment["user_id"]) != str(session["user_id"]):
            abort(403)

        cursor.execute("""
            UPDATE comments
            SET content = %s
            WHERE id = %s
              AND post_id = %s
              AND user_id = %s
        """, (
            content,
            comment_id,
            post_id,
            comment["user_id"]
        ))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )
# =========================
# 댓글 삭제
# =========================
@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/delete",
    methods=["POST"]
)
def comment_delete(post_id, comment_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id
            FROM comments
            WHERE id = %s
              AND post_id = %s
        """, (comment_id, post_id))

        comment = cursor.fetchone()

        if not comment:
            abort(404)

        is_author = (
            comment["user_id"] is not None
            and str(comment["user_id"]) == str(session["user_id"])
        )

        is_admin = (
            session.get("role") == "admin"
        )

        if not (is_author or is_admin):
            abort(403)

        cursor.execute("""
            DELETE FROM comments
            WHERE id = %s
              AND post_id = %s
        """, (comment_id, post_id))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    return redirect(
        url_for(
            "community.community_detail",
            post_id=post_id
        )
    )