from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import get_connection


auth_bp = Blueprint("auth", __name__)


# ==============================
# 회원가입
# ==============================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("auth/register.html")


    # 입력값 받기
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    nickname = request.form.get("nickname", "").strip()
    email = request.form.get("email", "").strip()


    # ==============================
    # 기본 입력 검사
    # ==============================

    if not username:
        return "아이디를 입력해주세요.", 400

    if not password:
        return "비밀번호를 입력해주세요.", 400

    if not password_confirm:
        return "비밀번호 확인을 입력해주세요.", 400

    if not nickname:
        return "닉네임을 입력해주세요.", 400

    if not email:
        return "이메일을 입력해주세요.", 400


    # 아이디 길이
    if len(username) < 4 or len(username) > 20:
        return "아이디는 4~20자로 입력해주세요.", 400


    # 비밀번호 길이
    if len(password) < 8:
        return "비밀번호는 8자 이상으로 입력해주세요.", 400


    # 비밀번호 확인
    if password != password_confirm:
        return "비밀번호가 일치하지 않습니다.", 400


    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ==============================
        # 아이디 중복 확인
        # ==============================

        cursor.execute("""
            SELECT id
            FROM users
            WHERE username = %s
        """, (username,))

        if cursor.fetchone():
            return "이미 사용 중인 아이디입니다.", 400


        # ==============================
        # 닉네임 중복 확인
        # ==============================

        cursor.execute("""
            SELECT id
            FROM users
            WHERE nickname = %s
        """, (nickname,))

        if cursor.fetchone():
            return "이미 사용 중인 닉네임입니다.", 400


        # ==============================
        # 이메일 중복 확인
        # ==============================

        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = %s
        """, (email,))

        if cursor.fetchone():
            return "이미 가입된 이메일입니다.", 400


        # ==============================
        # 비밀번호 암호화
        # ==============================

        hashed_password = generate_password_hash(password)


        # ==============================
        # 회원 저장
        # ==============================

        cursor.execute("""
            INSERT INTO users (
                username,
                password,
                nickname,
                email
            )
            VALUES (%s, %s, %s, %s)
        """, (
            username,
            hashed_password,
            nickname,
            email
        ))

        conn.commit()


    except Exception as e:

        conn.rollback()

        print("회원가입 오류:", e)

        return "회원가입 중 오류가 발생했습니다.", 500


    finally:

        cursor.close()
        conn.close()


    # 회원가입 성공 → 로그인 화면
    return redirect("/login")

# ==============================
# 아이디 중복 확인
# ==============================

@auth_bp.route("/register/check-username", methods=["GET"])
def check_username():

    username = request.args.get("username", "").strip()

    if not username:
        return {
            "available": False,
            "message": "아이디를 입력해주세요."
        }

    if len(username) < 4 or len(username) > 20:
        return {
            "available": False,
            "message": "아이디는 4~20자로 입력해주세요."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE username = %s
    """, (username,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return {
            "available": False,
            "message": "이미 사용 중인 아이디입니다."
        }

    return {
        "available": True,
        "message": "사용 가능한 아이디입니다."
    }


# ==============================
# 닉네임 중복 확인
# ==============================

@auth_bp.route("/register/check-nickname", methods=["GET"])
def check_nickname():

    nickname = request.args.get("nickname", "").strip()

    if not nickname:
        return {
            "available": False,
            "message": "닉네임을 입력해주세요."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE nickname = %s
    """, (nickname,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return {
            "available": False,
            "message": "이미 사용 중인 닉네임입니다."
        }

    return {
        "available": True,
        "message": "사용 가능한 닉네임입니다."
    }


# ==============================
# 이메일 중복 확인
# ==============================

@auth_bp.route("/register/check-email", methods=["GET"])
def check_email():

    email = request.args.get("email", "").strip()

    if not email:
        return {
            "available": False,
            "message": "이메일을 입력해주세요."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = %s
    """, (email,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return {
            "available": False,
            "message": "이미 사용 중인 이메일입니다."
        }

    return {
        "available": True,
        "message": "사용 가능한 이메일입니다."
    }

# ==============================
# 로그인
# ==============================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            username,
            password,
            nickname
        FROM users
        WHERE username = %s
    """, (username,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user or not check_password_hash(
        user["password"],
        password
    ):
        return "아이디 또는 비밀번호가 올바르지 않습니다."

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["nickname"] = user["nickname"]

    return redirect("/")


# ==============================
# 로그아웃
# ==============================

@auth_bp.route("/logout")
def logout():

    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("nickname", None)

    return redirect("/")