from flask import Blueprint, render_template, request, session, redirect, jsonify

from db import get_connection
from .breed_classifier import predict_breed


dog_bp = Blueprint("dog", __name__)


@dog_bp.route("/dog/register", methods=["GET", "POST"])
def dog_register():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    # 반려견 등록 화면
    if request.method == "GET":
        return render_template("dog/dog_register.html")

    name = request.form.get("name")
    breed = request.form.get("breed")
    size_category = request.form.get("size_category")
    birth_date = request.form.get("birth_date")
    personality = request.form.get("personality")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO dogs (
            user_id,
            name,
            breed,
            size_category,
            birth_date,
            personality
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        name,
        breed,
        size_category,
        birth_date if birth_date else None,
        personality
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dogs")


@dog_bp.route("/dogs")
def dog_list():

    # 로그인하지 않은 경우
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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
        ORDER BY created_at DESC
    """, (session["user_id"],))

    dogs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dog/dog_list.html",
        dogs=dogs
    )


@dog_bp.route("/dog/edit/<int:dog_id>", methods=["GET", "POST"])
def dog_edit(dog_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 현재 로그인한 사용자의 반려견인지 확인
    cursor.execute("""
        SELECT
            id,
            name,
            breed,
            size_category,
            birth_date,
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
        cursor.close()
        conn.close()
        return "반려견을 찾을 수 없습니다.", 404

    # 수정 화면
    if request.method == "GET":
        cursor.close()
        conn.close()

        return render_template(
            "dog/dog_edit.html",
            dog=dog
        )

    # 수정된 값 받기
    name = request.form.get("name")
    breed = request.form.get("breed")
    size_category = request.form.get("size_category")
    birth_date = request.form.get("birth_date")
    personality = request.form.get("personality")

    cursor.execute("""
        UPDATE dogs
        SET
            name = %s,
            breed = %s,
            size_category = %s,
            birth_date = %s,
            personality = %s
        WHERE id = %s
          AND user_id = %s
    """, (
        name,
        breed,
        size_category,
        birth_date if birth_date else None,
        personality,
        dog_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/mypage")


@dog_bp.route("/dog/delete/<int:dog_id>", methods=["POST"])
def dog_delete(dog_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # 현재 로그인한 사용자의 반려견만 삭제
    cursor.execute("""
        DELETE FROM dogs
        WHERE id = %s
          AND user_id = %s
    """, (
        dog_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/dogs")

@dog_bp.route("/dog/predict-breed", methods=["POST"])
def dog_predict_breed():
    # 로그인 확인
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다."
        }), 401

    # 이미지가 전송됐는지 확인
    if "image" not in request.files:
        return jsonify({
            "success": False,
            "message": "사진을 선택해주세요."
        }), 400

    image_file = request.files["image"]

    # 파일명이 비어있는 경우
    if image_file.filename == "":
        return jsonify({
            "success": False,
            "message": "사진을 선택해주세요."
        }), 400

    try:
        # 업로드된 이미지를 바로 AI에 전달
        results = predict_breed(image_file.stream)

        return jsonify({
            "success": True,
            "predictions": results
        })

    except Exception as e:
        print("견종 분석 오류:", e)

        return jsonify({
            "success": False,
            "message": "견종 분석 중 오류가 발생했습니다."
        }), 500
