# FULL CODE TỐI ƯU – BUFF VIEW TIKTOK 2025 (TẢI DEVICE TỪ FILE device.txt)
# Đã thay API endpoint từ api16 sang api22.

import datetime
import random
import requests
import re
import threading
import time
from hashlib import md5
from time import time as T
import secrets
from typing import Optional, Dict
import json # Thêm thư viện JSON

# ======================================================
#   TẢI DEVICE CONFIG TỪ FILE device.txt
# ======================================================

def load_device_configs(path="device.txt"):
    """
    Tải danh sách cấu hình thiết bị từ file device.txt.
    Mỗi dòng là một cấu hình JSON.
    """
    configs = []
    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    config = json.loads(line)
                    # Kiểm tra các key cần thiết
                    required_keys = ["UA", "OS_API", "OS_VERSION", "BUILD_NUMBER", "APP_VERSION", "DEVICE_TYPE"]
                    if all(k in config for k in required_keys):
                        configs.append(config)
                    else:
                        print(f"[-] Cảnh báo: Cấu hình thiếu key bắt buộc, bỏ qua: {line[:50]}...")
                except json.JSONDecodeError:
                    print(f"[-] Cảnh báo: Lỗi định dạng JSON, bỏ qua dòng: {line[:50]}...")
    except FileNotFoundError:
        print("[!] Không tìm thấy file device.txt. Vui lòng tạo file này với cấu hình thiết bị JSON.")
    except Exception as e:
        print(f"[-] Lỗi không xác định khi đọc device.txt: {e}")
        
    if not configs:
        print("[CRITICAL] Không có cấu hình thiết bị nào được tải. Sử dụng cấu hình mặc định tạm thời.")
        # Cấu hình mặc định để tránh crash
        return [{
            "UA": "TikTok 38.1.0 rv:381000 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile",
            "OS_API": "24",
            "OS_VERSION": "18.3",
            "BUILD_NUMBER": "381000",
            "APP_VERSION": "38.1.0",
            "DEVICE_TYPE": "iPhone16,2",
        }]
    return configs

DEVICE_CONFIGS = load_device_configs()

# ======================================================
#   SIGNATURE ENGINE (KEEP ORIGINAL)
# ======================================================

class Signature:
    def __init__(self, params: str, data: str, cookies: str) -> None:
        self.params = params
        self.data = data
        self.cookies = cookies

    def hash(self, data: str) -> str:
        return str(md5(data.encode()).hexdigest())

    def calc_gorgon(self) -> str:
        gorgon = self.hash(self.params)
        if self.data:
            gorgon += self.hash(self.data)
        else:
            gorgon += str("0" * 32)
        if self.cookies:
            gorgon += self.hash(self.cookies)
        else:
            gorgon += str("0" * 32)
        gorgon += str("0" * 32)
        return gorgon

    def get_value(self):
        gorgon = self.calc_gorgon()
        return self.encrypt(gorgon)

    def encrypt(self, data: str):
        unix = int(T())
        key = [
            0xDF, 0x77, 0xB9, 0x40, 0xB9, 0x9B, 0x84, 0x83, 0xD1, 0xB9, 0xCB, 0xD1,
            0xF7, 0xC2, 0xB9, 0x85, 0xC3, 0xD0, 0xFB, 0xC3,
        ]
        len_key = len(key)

        param_list = []
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(H)

        param_list.extend([0x0, 0x6, 0xB, 0x1C])

        H = int(hex(unix), 16)
        param_list.append((H & 0xFF000000) >> 24)
        param_list.append((H & 0x00FF0000) >> 16)
        param_list.append((H & 0x0000FF00) >> 8)
        param_list.append((H & 0x000000FF))

        eor_result_list = [A ^ B for A, B in zip(param_list, key)]

        for i in range(len_key):
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % len_key]
            E = C ^ D
            F = self.rbit(E)
            H = ((F ^ 0xFFFFFFFF) ^ len_key) & 0xFF
            eor_result_list[i] = H

        result = "".join(self.hex_string(param) for param in eor_result_list)
        return {"X-Gorgon": ("840280416000" + result), "X-Khronos": str(unix)}

    def rbit(self, num):
        tmp = bin(num)[2:].zfill(8)
        return int(tmp[::-1], 2)

    def hex_string(self, num):
        return hex(num)[2:].zfill(2)

    def reverse(self, num):
        tmp = self.hex_string(num)
        return int(tmp[1:] + tmp[:1], 16)

# ======================================================
# LẤY VIDEO ID
# ======================================================

link = input('Link Video TIKTOK: ')
headers_id = {
    'User-Agent': random.choice(DEVICE_CONFIGS)['UA'],
    'Accept': 'text/html'
}

print("[+] Đang lấy ID video...")

try:
    page = requests.get(link, headers=headers_id, timeout=10).text
    # Tìm kiếm video ID trong JSON data của trang
    match = re.search(r'"video":\{"id":"(\d+)"', page)
    if not match:
        print("[-] Không tìm thấy ID video. Đảm bảo link là video công khai và không bị giới hạn khu vực.")
        exit(1)
    video_id = match.group(1)
    print(f"[+] ID VIDEO: {video_id}")
except Exception as e:
    print(f"[-] Lỗi khi lấy ID video: {e}")
    exit(1)


# ======================================================
# PROXY SYSTEM + AUTO REMOVE DEAD PROXY
# ======================================================

def load_proxies(path="proxy.txt"):
    proxies = []
    try:
        with open(path, "r", encoding="utf8") as f:
            for x in f:
                x = x.strip()
                if not x:
                    continue
                p = x.split(":")
                if len(p) == 4:
                    ip, port, user, pw = p
                    url = f"http://{user}:{pw}@{ip}:{port}"
                    proxies.append({"http": url, "https": url})
                elif len(p) == 2:
                    ip, port = p
                    url = f"http://{ip}:{port}"
                    proxies.append({"http": url, "https": url})
    except:
        print("[-] Không có proxy.txt – chạy bằng IP máy. Nên sử dụng proxy để chống spam tốt hơn.")
    return proxies

PROXIES = load_proxies()
BAD = set()
LOCK = threading.Lock()


def get_proxy():
    with LOCK:
        good = [p for p in PROXIES if str(p) not in BAD]
        if not good:
            if PROXIES:
                print("[!] Đã hết proxy tốt. Reset danh sách proxy xấu.")
                BAD.clear()
                good = PROXIES # Reset và chọn lại
            else:
                return None
        return random.choice(good)


# ======================================================
# FAKE DEVICE ID CHUẨN APPLE - Dành cho cấu hình không có CUSTOM_IDS
# ======================================================

def generate_apple_id(length=19):
    # Tạo ID ngẫu nhiên có độ dài 19, chuẩn TikTok iOS
    return str(random.randint(10**(length-1), (10**length)-1))


# ======================================================
# HANDLE RESPONSE
# ======================================================

def handle_response(resp: Dict):
    # TikTok thường trả về status_code=0 khi thành công (hoặc không báo lỗi)
    if "status_code" in resp and resp["status_code"] == 0:
        return True
    
    # Kiểm tra các thông báo lỗi chính để phân biệt thành công/thất bại
    if 'message' in resp and resp.get('message') == 'success':
        return True
    
    return False


# ======================================================
# MAIN SEND VIEW (Đã tích hợp sử dụng CUSTOM_IDS)
# ======================================================

count = 0

def send_view():
    global count

    session = requests.Session()

    while True:
        try:
            cfg = random.choice(DEVICE_CONFIGS)
            
            # --- PHẦN SỬ DỤNG CUSTOM ID TỪ device.txt ---
            if "CUSTOM_IDS" in cfg:
                # Định dạng ID tùy chỉnh: device_id:install_id:session_id:token_id
                try:
                    ids = cfg["CUSTOM_IDS"].split(":")
                    device_id = ids[0]
                    iid = ids[1]
                    # Token/sessionid có thể tái sử dụng nếu muốn, nhưng ngẫu nhiên tốt hơn
                    token = secrets.token_hex(16) 
                except:
                    # Fallback nếu định dạng ID trong file sai
                    device_id = generate_apple_id()
                    iid = generate_apple_id()
                    token = secrets.token_hex(16)
            else:
                # Sử dụng ID ngẫu nhiên nếu cấu hình không có CUSTOM_IDS
                device_id = generate_apple_id()
                iid = generate_apple_id()
                token = secrets.token_hex(16) # sessionid
            # ---------------------------------------------

            net = random.choice(["WIFI", "4G", "LTE", "5G"])

            # Xây dựng X-Common-Params-V2
            common = (
                f"pass-region=1&pass-route=1&language=vi"
                f"&version_code={cfg['APP_VERSION']}"
                f"&app_version={cfg['APP_VERSION']}"
                "&carrier_region=VN&channel=App%20Store&mcc_mnc=45201"
                f"&device_id={device_id}"
                "&tz_offset=25200&account_region=VN&sys_region=VN"
                "&aid=1233&screen_width=1125&uoo=1"
                f"&os_api={cfg['OS_API']}"
                f"&os_version={cfg['OS_VERSION']}"
                "&device_platform=iphone"
                f"&build_number={cfg['BUILD_NUMBER']}"
                f"&device_type={cfg['DEVICE_TYPE']}"
                f"&iid={iid}"
                "&locale=vi"
            )

            cookie = {"sessionid": token}

            # Tạo X-Gorgon và X-Khronos
            sig = Signature(
                params=f"ac={net}&op_region=VN",
                data='',
                cookies=str(cookie)
            ).get_value()

            data = {
                "action_time": int(time.time()),
                "aweme_type": 0,
                # Tăng độ ngẫu nhiên cho thời gian cài đặt đầu tiên (tính năng anti-spam)
                "first_install_time": int(time.time()) - random.randint(3600 * 24 * 7, 3600 * 24 * 30 * 6), # Từ 7 ngày đến 6 tháng
                "item_id": video_id,
                "play_delta": 1,
                "tab_type": 4
            }

            headers = {
                "User-Agent": cfg["UA"],
                "X-Gorgon": sig["X-Gorgon"],
                "X-Khronos": sig["X-Khronos"],
                "X-Common-Params-V2": common,
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "api22-core-c-alisg.tiktokv.com" # ĐÃ CẬP NHẬT HOST MỚI
            }

            # ĐÃ CẬP NHẬT API ENDPOINT MỚI
            url = f"https://api22-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?ac={net}&op_region=VN" 

            proxy = get_proxy()

            for attempt in range(3): # Retry 3 lần
                try:
                    r = session.post(
                        url,
                        data=data,
                        headers=headers,
                        cookies=cookie,
                        proxies=proxy,
                        timeout=10
                    )
                    resp = r.json()

                    if handle_response(resp):
                        # Cập nhật tổng số view thành công
                        with LOCK:
                            count += 1
                        print(f"[OK] +1 view | Total: {count} | Device ID: {device_id[:8]}... | UA: {cfg['APP_VERSION']}")
                        break
                    else:
                        # Thất bại nhưng không phải do kết nối/proxy
                        if attempt == 2:
                            print(f"[FAIL] Server Error | Resp: {resp.get('status_msg', 'No msg')[:30]} | Device ID: {device_id[:8]}...")
                except requests.exceptions.Timeout:
                    if proxy:
                        with LOCK:
                            BAD.add(str(proxy))
                    if attempt == 2:
                        print("[FAIL] Proxy/Timeout - Bỏ qua proxy này.")
                except Exception as e:
                    # Lỗi kết nối khác (DNS, Connection Refused,...)
                    if attempt == 2:
                        print(f"[FAIL] Connection Error: {e.__class__.__name__} | Device ID: {device_id[:8]}...")
                
                # Giảm thời gian chờ giữa các lần thử lại trong cùng 1 request
                time.sleep(random.uniform(0.1, 0.3))

            # Giảm thời gian chờ giữa các request
            time.sleep(random.uniform(0.03, 0.10))

        except Exception as e:
            # Lỗi không mong muốn trong vòng lặp chính
            pass


# ======================================================
# START THREADS
# ======================================================

NUM_THREADS = 600   # Mức khuyến nghị

print("="*50)
print(f"       TIKTOK VIEW BOT - STARTING (API 22)")
print("="*50)
print(f"[+] Tổng cộng {len(DEVICE_CONFIGS)} cấu hình thiết bị (UA) được tải.")
print(f"[+] Running with {NUM_THREADS} threads.")
print(f"[+] Loaded {len(PROXIES)} proxies.")
print("="*50)

for _ in range(NUM_THREADS):
    t = threading.Thread(target=send_view)
    t.daemon = True
    t.start()

# Giữ main thread chạy để các worker thread tiếp tục làm việc
while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Dừng chương trình theo yêu cầu.")
        break