from flask import render_template, session, abort, redirect
from db import get_connection
from . import admin_bp


@admin_bp.before_request
def check_admin():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT role
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()

    finally:
        cursor.close()
        conn.close()

    if not user or user["role"] != "admin":
        abort(403)


# ==============================
# 관리자 통합 대시보드
# ==============================
@admin_bp.route("/")
def dashboard():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 전체 회원
        cursor.execute("""
            SELECT id, username, nickname, role
            FROM users
            ORDER BY id DESC
        """)
        users = cursor.fetchall()

        # 전체 게시글
        cursor.execute("""
            SELECT id, author, title, created_at
            FROM posts
            ORDER BY id DESC
        """)
        posts = cursor.fetchall()

        # 전체 댓글
        cursor.execute("""
            SELECT
                c.id,
                c.post_id,
                c.author,
                c.content,
                c.created_at,
                p.title AS post_title
            FROM comments c
            JOIN posts p ON c.post_id = p.id
            ORDER BY c.id DESC
        """)
        comments = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/dashboard.html",
        user_count=len(users),
        post_count=len(posts),
        comment_count=len(comments),
        users=users,
        posts=posts,
        comments=comments
    )

# ==============================
# 관리자 - 게시글 목록
# ==============================
@admin_bp.route("/posts")
def manage_posts():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id, author, title, created_at
            FROM posts
            ORDER BY id DESC
        """)
        items = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/manage.html",
        items=items,
        mode="posts"
    )


# ==============================
# 관리자 - 댓글 목록
# ==============================
@admin_bp.route("/comments")
def manage_comments():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                c.id,
                c.post_id,
                c.author,
                c.content,
                c.created_at,
                p.title AS post_title
            FROM comments c
            JOIN posts p ON c.post_id = p.id
            ORDER BY c.id DESC
        """)
        items = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/manage.html",
        items=items,
        mode="comments"
    )


# ==============================
# 관리자 - 게시글 삭제
# ==============================
@admin_bp.route(
    "/posts/<int:post_id>/delete",
    methods=["POST"]
)
def admin_delete_post(post_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 댓글부터 삭제
        cursor.execute("""
            DELETE FROM comments
            WHERE post_id = %s
        """, (post_id,))

        # 게시글 삭제
        cursor.execute("""
            DELETE FROM posts
            WHERE id = %s
        """, (post_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return redirect("/admin/")


# ==============================
# 관리자 - 댓글 삭제
# ==============================
@admin_bp.route(
    "/comments/<int:comment_id>/delete",
    methods=["POST"]
)
def admin_delete_comment(comment_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM comments
            WHERE id = %s
        """, (comment_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return redirect("/admin/")