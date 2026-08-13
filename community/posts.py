from flask import render_template, request, redirect, url_for
from db import get_connection

from . import community
from .utils import save_image


# =========================
# 게시글 목록
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
        "community/community.html",
        posts=posts
    )


# =========================
# 게시글 작성
# =========================
@community.route("/community/write", methods=["GET", "POST"])
def community_write():

    if request.method == "GET":
        return render_template(
            "community/community_write.html"
        )

    author = request.form.get(
        "author",
        ""
    ).strip()

    title = request.form.get(
        "title",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if (
        not author
        or not title
        or not content
    ):
        return (
            "작성자, 제목, 내용을 모두 입력해주세요.",
            400
        )

    # 이미지 업로드
    image_file = request.files.get("image")

    image_path = save_image(
        image_file
    )

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
            id,
            post_id,
            author,
            content,
            created_at,
            updated_at
        FROM comments
        WHERE post_id = %s
        ORDER BY id ASC
    """, (
        post_id,
    ))

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

    conn = get_connection()
    cursor = conn.cursor(
        dictionary=True
    )

    # 수정 페이지
    if request.method == "GET":

        cursor.execute("""
            SELECT
                id,
                author,
                title,
                content
            FROM posts
            WHERE id = %s
        """, (
            post_id,
        ))

        post = cursor.fetchone()

        cursor.close()
        conn.close()

        if not post:
            return (
                "게시글을 찾을 수 없습니다.",
                404
            )

        return render_template(
            "community/community_edit.html",
            post=post
        )

    # 수정 저장
    author = request.form.get(
        "author",
        ""
    ).strip()

    title = request.form.get(
        "title",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if (
        not author
        or not title
        or not content
    ):
        cursor.close()
        conn.close()

        return (
            "작성자, 제목, 내용을 모두 입력해주세요.",
            400
        )

    cursor.execute("""
        UPDATE posts
        SET
            author = %s,
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


# =========================
# 게시글 삭제
# =========================
@community.route(
    "/community/<int:post_id>/delete",
    methods=["POST"]
)
def community_delete(post_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM posts
        WHERE id = %s
    """, (
        post_id,
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
# 댓글 작성
# =========================
@community.route(
    "/community/<int:post_id>/comments",
    methods=["POST"]
)
def comment_create(post_id):

    author = request.form.get(
        "author",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not author or not content:
        return (
            "작성자와 댓글 내용을 입력해주세요.",
            400
        )

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


# =========================
# 댓글 수정
# =========================
@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/edit",
    methods=["POST"]
)
def comment_edit(
    post_id,
    comment_id
):

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not content:
        return (
            "댓글 내용을 입력해주세요.",
            400
        )

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


# =========================
# 댓글 삭제
# =========================
@community.route(
    "/community/<int:post_id>/comments/<int:comment_id>/delete",
    methods=["POST"]
)
def comment_delete(
    post_id,
    comment_id
):

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