import os
import uuid
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = os.path.join("static", "uploads")

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


# uploads 폴더가 없으면 자동 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def save_image(file):

    # 파일을 첨부하지 않은 경우
    if not file or file.filename == "":
        return None

    # 허용되지 않은 확장자
    if not allowed_file(file.filename):
        return None

    original_name = secure_filename(file.filename)

    extension = original_name.rsplit(
        ".",
        1
    )[1].lower()

    # 파일명 중복 방지를 위해 UUID 사용
    new_filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    save_path = os.path.join(
        UPLOAD_FOLDER,
        new_filename
    )

    file.save(save_path)

    # DB에는 static 기준 상대경로 저장
    return f"uploads/{new_filename}"