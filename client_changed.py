import requests
import os
import base64
import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

BASE_URL = "http://127.0.0.1:5000"
SECRET_KEY = b'0123456789abcdef'  # Khóa mã hóa

# DƯƠNG ĐỨC HUY
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


# Tải lên ghi chú
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
        
    # Ensure the response is JSON before accessing it
    try:
        response_json = response.json()
        print(response_json["message"])
    except requests.exceptions.JSONDecodeError:
        print("Error: Response is not in JSON format.")


# Tải xuống ghi chú
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


# VÕ NGUYỄN GIA HƯNG
# Lấy danh sách ghi chú
def list_notes(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/get-files", headers=headers)
    if response.status_code == 200:
        files = response.json().get("files", [])

        if not files:
            print("Không có tệp tin nào")
        else:
            print("Danh sách ghi chú:")
            for idx, file in enumerate(files):
                print(f"ID: {idx}, Nội dung: {file['file_name']}")
        return files

    else:
        print(response.json())
        return []

# Xóa ghi chú
def delete_note(token, note_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{BASE_URL}/delete-note/{note_id}", headers=headers)
    return response.status_code == 200

# Chia sẻ ghi chú
def share_note(token, note_id, minutes=60):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/share-note/{note_id}", json={"hours": minutes / 60}, 
                              headers=headers)
                              
    if response.status_code == 200:
        return response.json()
    else:
        error_message = response.json().get('error', 'Lỗi không xác định')
        print(error_message)
        return None

# Truy cập ghi chú được chia sẻ
def access_shared_note(share_url):
    try:
        response = requests.get(share_url)
        response.raise_for_status()
        data = response.json()
        return data.get("note")
    except requests.exceptions.RequestException as req_err:
        print(f"Error accessing shared note: {req_err}")
        return None

# Xóa ghi chú đã chia sẻ
def cancel_shared_note(token, share_url):
    # Tách ID ghi chú từ URL
    share_id = share_url.split('/')[-1]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(f"{BASE_URL}/cancel-share/{share_id}", headers=headers)
    
    if response.status_code == 200:
        print("Đã hủy chia sẻ ghi chú")
        return True
    else:
        print("Ghi chú không tồn tại hoặc đã hết hạn")
        return False

# Hiển thị menu
def show_menu():
    print("1. Đăng ký")
    print("2. Đăng nhập")
    print("3. Thoát")
    choice = input("Chọn lựa chọn của bạn: ")
    
    if choice == "1":
        username = input("Nhập tên người dùng: ")
        password = input("Nhập mật khẩu: ")
        if register(username, password):
            print("Đăng ký thành công!")
        else:
            print("Tên người dùng đã tồn tại.")
    
    elif choice == "2":
        username = input("Nhập tên người dùng: ")
        password = input("Nhập mật khẩu: ")
        token = login(username, password)
        if token:
            print("Đăng nhập thành công!")
            after_login_menu(token)
        else:
            print("Thông tin đăng nhập không chính xác.")

    elif choice == "3":
        print("Thoát chương trình.")
        exit()


# Menu sau khi đăng nhập
def after_login_menu(token):
    while True:
        print("\n--- Quản lý ghi chú ---")
        print("1. Lấy danh sách ghi chú")
        print("2. Tải lên ghi chú")
        print("3. Tải xuống ghi chú")
        print("4. Xóa ghi chú")
        print("5. Chia sẻ ghi chú")
        print("6. Truy cập ghi chú được chia sẻ")
        print("7. Hủy chia sẻ ghi chú")    
        print("8. Thoát")

        choice = input("Chọn chức năng: ")

        if choice == "1":
            notes = list_notes(token)

        elif choice == "2":
            file_path = input("Đường dẫn tệp tin: ")
            if os.path.exists(file_path):
                upload_file(token, file_path)
            else:
                print("Tệp tin không tồn tại.")

        elif choice == "3":
            username = input("Nhập tên người dùng: ")
            get_files(token, username)

        elif choice == "4":
            note_id = int(input("Nhập ID ghi chú muốn xóa: "))
            if delete_note(token, note_id):
                print("Ghi chú đã được xóa!")
            else:
                print("Không thể xóa ghi chú.")

        elif choice == "5":
            notes = list_notes(token)

            if not notes:
                print("Không tồn tại ghi chú nào.")
                continue

            note_id = int(input("Nhập ID ghi chú muốn chia sẻ: "))

            if 0 <= note_id < len(notes):
                minutes = int(input("Nhập số phút hiệu lực (mặc định 60): ") or 60)
                shared_info = share_note(token, note_id, minutes)

                if shared_info:
                    print(f"URL chia sẻ: {shared_info['share_url']}")

                    expires_at = datetime.datetime.fromisoformat(shared_info['expires_at'])
                    expires_at += datetime.timedelta(hours=7)  # Chuyển sang timezone UTC+7
                    formatted_expires_at = expires_at.strftime("%d-%m-%y, %H:%M:%S")
                    print(f"Hết hạn vào: {formatted_expires_at}")
            else:
                print("ID ghi chú không hợp lệ.")
                
        elif choice == "6":
            share_url = input("Nhập URL ghi chú được chia sẻ: ")
            shared_note = access_shared_note(share_url)
            if shared_note:
                print("Nội dung ghi chú:")
                print(shared_note)
            else:
                print("Không thể truy cập ghi chú.")
    
        elif choice == "7":
            share_url = input("Nhập URL ghi chú được chia sẻ: ")
            cancel_shared_note(token, share_url)

        elif choice == "8":
            print("Thoát.")
            break

# Chạy chương trình
if __name__ == "__main__":
    while True:
        show_menu()