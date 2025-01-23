import os
import json
import bcrypt
import jwt
import datetime
import uuid
import base64
import logging
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

# Khởi tạo Flask
app = Flask(__name__)

# Cấu hình  
SECRET_KEY = b'0123456789abcdef'  # Khóa mã hóa
DB_FILE = os.path.join(os.path.dirname(__file__), "db.json")
SHARED_NOTES_DIR = "shared_notes"  # Thư mục chứa ghi chú được chia sẻ

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)

# DƯƠNG ĐỨC HUY
# Hàm tiện ích quản lý database
def load_database():
    if not os.path.exists(DB_FILE):
        # Nếu tệp không tồn tại, tạo một tệp mới với dữ liệu mặc định
        with open(DB_FILE, "w") as file:
            json.dump({"users": {}, "notes": {}}, file, indent=4)
        return {"users": {}, "notes": {}}
    try:
        # Cố gắng đọc dữ liệu từ tệp nếu tệp tồn tại
        with open(DB_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        # Nếu tệp bị lỗi (ví dụ: không phải JSON hợp lệ), tạo lại cơ sở dữ liệu mặc định
        with open(DB_FILE, "w") as file:
            json.dump({"users": {}, "notes": {}}, file, indent=4)
        return {"users": {}, "notes": {}}


def save_database(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)


# Tạo JWT
def create_token(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# Xác thực JWT
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["username"]
    except jwt.ExpiredSignatureError:
        return None  # Token hết hạn
    except jwt.InvalidTokenError:
        return None  # Token không hợp lệ


# API Đăng ký
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = load_database()
    if username in db["users"]:
        return jsonify({"error": "Tên người dùng đã tồn tại!"}), 400

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    db["users"][username] = {"password": hashed_password.decode()}  # Lưu password đã hash
    db["notes"][username] = []  # Tạo danh sách ghi chú trống
    save_database(db)
    return jsonify({"message": "Đăng ký thành công!"})


# API Đăng nhập
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = load_database()
    user = db["users"].get(username)
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Sai thông tin đăng nhập!"}), 401

    token = create_token(username)
    return jsonify({"token": token})

    return "Login endpoint"


# API Upload ghi chú
@app.route("/upload-file", methods=["POST"])
def upload_file():
    token = request.headers.get("Authorization").split(" ")[1]
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    data = request.json
    file_name, encrypted_file = data.get("file_name"), data.get("encrypted_file")
    if not file_name or not encrypted_file:
        return jsonify({"error": "Dữ liệu không hợp lệ!"}), 400

    db = load_database()
    if "files" not in db:
        db["files"] = {}
    if username not in db["files"]:
        db["files"][username] = []
    db["files"][username].append({"file_name": file_name, "encrypted_file": encrypted_file})
    save_database(db)
    return jsonify({"message": "Tệp tin đã được tải lên!"})


# API Download ghi chú
@app.route("/get-files", methods=["GET"])
def get_files():
    token = request.headers.get("Authorization").split(" ")[1]
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    db = load_database()
    user_files = db["files"].get(username, [])
    return jsonify({"files": user_files})


# VÕ NGUYỄN GIA HƯNG
# Tạo URL chia sẻ
def generate_share_url(note_id, expiration_time):
    # Định dạng URL chia sẻ
    return f"http://127.0.0.1:5000/shared/{note_id}"


# API Lấy danh sách ghi chú
@app.route("/list-notes", methods=["GET"])
def list_notes():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify({"error": "Token không được cung cấp!"}), 401

    token = auth_header.split(" ")[1]
    username = verify_token(token)

    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    db = load_database()
    user_notes = db["notes"].get(username, [])
    
    # Return note IDs and some metadata
    note_list = [{"id": idx, "encrypted_note": note} for idx, note in enumerate(user_notes)]
    return jsonify({"notes": note_list})


# API Xóa ghi chú
@app.route("/delete-note/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify({"error": "Token không được cung cấp!"}), 401

    token = auth_header.split(" ")[1]
    username = verify_token(token)

    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    db = load_database()
    user_files = db["files"].get(username, [])
    
    if 0 <= note_id < len(user_files):
        del user_files[note_id]
        db["files"][username] = user_files
        save_database(db)
        return jsonify({"message": "Tệp tin đã được xóa!"})
    
    return jsonify({"error": "Tệp tin không tồn tại!"}), 404


# API Chia sẻ ghi chú
@app.route("/share-note/<int:note_id>", methods=["POST"])
def share_note(note_id):
    try:
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Token không được cung cấp!"}), 401

        token = auth_header.split(" ")[1]
        username = verify_token(token)

        if not username:
            return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

        # Lấy thời gian hết hạn từ yêu cầu, mặc định là 1 giờ
        data = request.json
        hours = data.get('hours', 1)
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=hours)

        db = load_database()
        user_files = db["files"].get(username, [])

        if 0 <= note_id < len(user_files):
            share_id = str(uuid.uuid4())
            if "shared_notes" not in db:
                db["shared_notes"] = {}
            db["shared_notes"][share_id] = {
                "username": username,
                "file_name": user_files[note_id]["file_name"],
                "encrypted_file": user_files[note_id]["encrypted_file"],
                "expires_at": expiration_time.isoformat()
            }
            save_database(db)
            return jsonify({"share_url": generate_share_url(share_id, expiration_time), 
                            "expires_at": expiration_time.isoformat()})

        return jsonify({"error": "Tệp tin không tồn tại!"}), 404
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"error": "Đã xảy ra lỗi!"}), 500


# API Truy cập ghi chú chia sẻ
@app.route("/shared/<share_id>", methods=["GET"])
def get_shared_note(share_id):
    db = load_database()
    shared_note = db["shared_notes"].get(share_id)
    if shared_note:

        if datetime.datetime.fromisoformat(shared_note["expires_at"]) > datetime.datetime.utcnow():
            return jsonify({
                "username": shared_note["username"],
                "note": shared_note["encrypted_file"]
            })
        else:
            return jsonify({"error": "Ghi chú đã hết hạn!"}), 410
            
    return jsonify({"error": "Ghi chú không tồn tại!"}), 404


# API Hủy chia sẻ ghi chú
@app.route("/cancel-share/<share_id>", methods=["DELETE"])
def cancel_shared_note(share_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token không được cung cấp!"}), 401

    token = auth_header.split(" ")[1]
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    db = load_database()
    shared_notes = db.get("shared_notes", {})

    if share_id not in shared_notes:
        return jsonify({"error": "Ghi chú không tồn tại."}), 404

    # Check if the shared note belongs to the current user
    if shared_notes[share_id]["username"] == username:
        del shared_notes[share_id]
        db["shared_notes"] = shared_notes
        save_database(db)
        return jsonify({"message": "Đã hủy chia sẻ ghi chú"}), 200
    else:
        return jsonify({"error": "Bạn không có quyền hủy chia sẻ này"}), 403

if __name__ == "__main__":
    # Tạo file cơ sở dữ liệu nếu chưa tồn tại
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as file:
            json.dump({"users": {}, "notes": {}, "shared_notes": {}}, file, indent=4)

    app.run(host='127.0.0.1', port=5000, debug=True)