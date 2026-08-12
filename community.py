from flask import Blueprint, render_template, request, redirect, url_for
from db import get_connection

community = Blueprint("community", __name__)


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
        "community.html",
        posts=posts
    )

@community.route("/community/write", methods=["GET", "POST"])
def community_write():

    # 글쓰기 화면 접속
    if request.method == "GET":
        return render_template("community_write.html")

    # 작성한 내용 받기
    author = request.form.get("author", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    # 필수값 확인
    if not author or not title or not content:
        return "작성자, 제목, 내용을 모두 입력해주세요.", 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts (author, title, content)
        VALUES (%s, %s, %s)
    """, (
        author,
        title,
        content
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("community.community_list"))

@community.route("/community/<int:post_id>")
def community_detail(post_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, author, title, content, image_path,
               created_at, updated_at
        FROM posts
        WHERE id = %s
    """, (post_id,))

    post = cursor.fetchone()

    cursor.close()
    conn.close()

    if not post:
        return "게시글을 찾을 수 없습니다.", 404

    return render_template(
        "community_detail.html",
        post=post
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
            "community_edit.html",
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