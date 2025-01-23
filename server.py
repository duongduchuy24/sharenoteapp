import os
import json
from flask import Flask, request, jsonify
import bcrypt
import jwt
import datetime

app = Flask(__name__)

SECRET_KEY = b'0123456789abcdef'
DB_FILE = os.path.join(os.path.dirname(__file__), "db.json")

def load_database():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as file:
            json.dump({"users": {}, "files": {}}, file, indent=4)
    with open(DB_FILE, "r") as file:
        return json.load(file)

def save_database(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

def create_token(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["username"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username, password = data.get("username"), data.get("password")
    db = load_database()

    if username in db["users"]:
        return jsonify({"error": "Tên người dùng đã tồn tại!"}), 400
    db["users"][username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db["files"][username] = []
    save_database(db)
    return jsonify({"message": "Đăng ký thành công!"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username, password = data.get("username"), data.get("password")
    db = load_database()

    if username not in db["users"] or not bcrypt.checkpw(password.encode(), db["users"][username].encode()):
        return jsonify({"error": "Sai thông tin đăng nhập!"}), 401
    token = create_token(username)
    return jsonify({"token": token})

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
    db["files"][username].append({"file_name": file_name, "encrypted_file": encrypted_file})
    save_database(db)
    return jsonify({"message": "Tệp tin đã được tải lên!"})

@app.route("/get-files", methods=["GET"])
def get_files():
    token = request.headers.get("Authorization").split(" ")[1]
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn!"}), 401

    db = load_database()
    user_files = db["files"].get(username, [])
    return jsonify({"files": user_files})

if __name__ == "__main__":
    app.run(debug=True)
