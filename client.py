import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import os
import base64

BASE_URL = "http://127.0.0.1:5000"
SECRET_KEY = b'0123456789abcdef'  # Khóa mã hóa (16 bytes)

# Mã hóa file
def encrypt_file(file_data, key):
    iv = os.urandom(16)  # Tạo IV ngẫu nhiên
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))  # Khởi tạo AES với CBC mode
    encryptor = cipher.encryptor()

    # Padding cho dữ liệu trước khi mã hóa
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(file_data) + padder.finalize()

    # Mã hóa dữ liệu đã padding
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Kết hợp IV và dữ liệu mã hóa, sau đó mã hóa base64
    return base64.b64encode(iv + encrypted_data).decode()

# Giải mã file
def decrypt_file(encrypted_file, key):
    encrypted_data = base64.b64decode(encrypted_file)
    iv = encrypted_data[:16]  # IV là 16 byte đầu tiên
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))  # Khởi tạo AES với CBC mode
    decryptor = cipher.decryptor()

    # Giải mã dữ liệu
    padded_data = decryptor.update(encrypted_data[16:]) + decryptor.finalize()

    # Loại bỏ padding
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded_data) + unpadder.finalize()

# Đăng ký
def register(username, password):
    response = requests.post(f"{BASE_URL}/register", json={"username": username, "password": password})
    if response.status_code == 200:
        print("Đăng ký thành công!")
    else:
        print(response.json()["error"])

# Đăng nhập
def login(username, password):
    response = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(response.json()["error"])
        return None

# Tải lên tệp tin
def upload_file(token, file_path):
    with open(file_path, "rb") as file:
        file_data = file.read()
    encrypted_file = encrypt_file(file_data, SECRET_KEY)

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/upload-file",
        json={"file_name": os.path.basename(file_path), "encrypted_file": encrypted_file},
        headers=headers
    )
    print(response.json()["message"])




# Tải xuống tệp tin
def get_files(token, username):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/get-files", headers=headers)
    
    if response.status_code == 200:
        files = response.json().get("files", [])
        
        # Tạo thư mục cho username nếu chưa tồn tại
        user_folder = os.path.join(os.getcwd(), username)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        
        for file in files:
            file_name = file["file_name"]
            encrypted_file = file["encrypted_file"]
            file_data = decrypt_file(encrypted_file, SECRET_KEY)

            # Lưu file vào thư mục người dùng
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, "wb") as f:
                f.write(file_data)
            print(f"Đã tải xuống: {file_name} vào thư mục {user_folder}")
    else:
        print(response.json().get("error"))

# Hiển thị menu chính
def show_menu():
    while True:
        print("\n1. Đăng ký")
        print("2. Đăng nhập")
        print("3. Thoát")
        choice = input("Chọn: ")

        if choice == "1":
            username = input("Tên người dùng: ")
            password = input("Mật khẩu: ")
            register(username, password)
        elif choice == "2":
            username = input("Tên người dùng: ")
            password = input("Mật khẩu: ")
            token = login(username, password)
            if token:
                after_login_menu(token, username)
        elif choice == "3":
            print("Thoát chương trình.")
            break

# Menu sau đăng nhập
def after_login_menu(token, username):
    while True:
        print("\n1. Tải lên tệp tin")
        print("2. Tải xuống tệp tin")
        print("3. Đăng xuất")
        choice = input("Chọn: ")

        if choice == "1":
            file_path = input("Đường dẫn tệp tin: ")
            if os.path.exists(file_path):
                upload_file(token, file_path)
            else:
                print("Tệp tin không tồn tại.")
        elif choice == "2":
            get_files(token, username)
        elif choice == "3":
            print("Đăng xuất.")
            break

if __name__ == "__main__":
    show_menu()
