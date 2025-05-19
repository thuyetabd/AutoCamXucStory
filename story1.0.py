import requests
import re
import json
from urllib.parse import urlparse, unquote, urljoin
import time
from collections import defaultdict
import base64
import os
from bs4 import BeautifulSoup

GRAPHQL_URL = "https://www.facebook.com/api/graphql/"

A_C = {
    "AUTHOR": "Phan Đình Thuyết",
    "FACEBOOK_URL": "https://www.facebook.com/phandinhthuyet/"
}

WWW_FB_DOMAIN = "https://www.facebook.com"
WWW_LOGIN_URL_GET = f"{WWW_FB_DOMAIN}/"

DEFAULT_POST_URL = "https://www.facebook.com/login.php"

def display_banner():
    author_name = A_C["AUTHOR"]
    fb_url = A_C["FACEBOOK_URL"]
    banner = f"""
    *****************************************************************
    *        TOOL TƯƠNG TÁC STORY FACEBOOK - PHIÊN BẢN 1.0        *
    *    Tác giả: {author_name.ljust(30)}      *
    *    Facebook: {fb_url.ljust(40)} *
    *****************************************************************
    """
    print(banner)

def load_cookies_from_file(filepath="cookie.txt"):
    cookies = {}
    try:
        with open(filepath, 'r') as f:
            cookie_str = f.read().strip()
        if not cookie_str:
            print(f"File {filepath} trống hoặc không chứa cookie.")
            return cookies
        for item in cookie_str.split(';'):
            parts = item.strip().split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        if not cookies:
            print(f"Không thể phân tích cookie từ {filepath}.")
        else:
            print(f"Đã tải cookie thành công từ {filepath}")
    except FileNotFoundError:
        print(f"File {filepath} không tìm thấy.")
    except Exception as e:
        print(f"Lỗi khi tải cookie từ file: {e}")
    return cookies

def save_cookies_to_file(session_cookies, filepath="cookie.txt"):

    if hasattr(session_cookies, 'items'): 
        cookies_to_save = session_cookies
    elif hasattr(session_cookies, 'get_dict'): 
        cookies_to_save = session_cookies.get_dict()
    else:
        print("Lỗi: Định dạng cookies không hỗ trợ để lưu.")
        return

    cookie_str = "; ".join([f"{name}={value}" for name, value in cookies_to_save.items()])
    try:
        with open(filepath, 'w') as f:
            f.write(cookie_str)
        print(f"Đã lưu cookie vào {filepath}")
    except Exception as e:
        print(f"Lỗi khi lưu cookie vào file: {e}")

def login_via_uid_pass(session, username, password, post_url=DEFAULT_POST_URL):
    """
    Thử đăng nhập Facebook bằng UID/Pass, dựa trên logic từ code.py.
    Nếu thành công, cookies sẽ được lưu vào session và file cookie.txt.
    Trả về True nếu có 'c_user' và 'xs' trong cookies sau khi thử đăng nhập, ngược lại False.
    """

    headers_get_and_post = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
    }
    
    current_headers = headers_get_and_post.copy()
    current_headers.update({
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    session.headers.update(current_headers)

    try:
        print(f"Đang truy cập trang đăng nhập: {WWW_LOGIN_URL_GET}")
        response_get = session.get(WWW_LOGIN_URL_GET, timeout=20)
        response_get.raise_for_status()
        print(f"  Status GET: {response_get.status_code}")

        soup_get = BeautifulSoup(response_get.text, 'html.parser')
        payload = {}
        
        login_form_element = soup_get.find('form', id='login_form')
        if not login_form_element: 
            login_form_element = soup_get.find('form', action=lambda x: x and 'login' in x)

        if login_form_element:
            hidden_inputs = login_form_element.find_all('input', type='hidden')
            for inp in hidden_inputs:
                name = inp.get('name')
                value = inp.get('value')
                if name:
                    payload[name] = value if value is not None else ""
            print(f"Đã thu thập {len(payload)} trường ẩn từ form.")
        else:
            print("CẢNH BÁO: Không tìm thấy form đăng nhập trên trang. Sẽ thử với các trường cơ bản.")

        payload['email'] = username
        payload['pass'] = password

        if 'lsd' not in payload:
            lsd_input = soup_get.find('input', {'name': 'lsd'})
            if lsd_input and lsd_input.get('value'):
                payload['lsd'] = lsd_input.get('value')
            else: 
                lsd_match_regex = re.search(r'name="lsd"[^>]*value="([^"]*)"', response_get.text)
                if lsd_match_regex: payload['lsd'] = lsd_match_regex.group(1)
        
        if 'jazoest' not in payload:
            jazoest_input = soup_get.find('input', {'name': 'jazoest'})
            if jazoest_input and jazoest_input.get('value'):
                payload['jazoest'] = jazoest_input.get('value')
            else: 
                jazoest_match_regex = re.search(r'name="jazoest"[^>]*value="([^"]*)"', response_get.text)
                if jazoest_match_regex: payload['jazoest'] = jazoest_match_regex.group(1)

        if login_form_element:
            submit_button_element = login_form_element.find('button', {'type':'submit', 'name':'login'})
            if submit_button_element and submit_button_element.get('value'):
                 payload['login'] = submit_button_element.get('value')
            elif not 'login' in payload : 
                 payload['login'] = 'Log In' 

        print("\nPayload sẽ được gửi (ẩn mật khẩu):")
        for k, v_payload in payload.items():
            print(f"  {k}: {'********' if k == 'pass' else str(v_payload)[:50]}") 
        
        if not payload.get('lsd') or not payload.get('jazoest'):
            print("CẢNH BÁO: Payload thiếu lsd hoặc jazoest. Khả năng thành công thấp.")

        post_request_headers = session.headers.copy()
        post_request_headers.update({
            "Referer": WWW_LOGIN_URL_GET,
            "Origin": WWW_FB_DOMAIN,
            "Content-Type": 'application/x-www-form-urlencoded',
            "Sec-Fetch-Site": "same-origin", 
            "Sec-Fetch-Dest": "document", 
        })

        if 'Sec-Fetch-User' in post_request_headers: del post_request_headers['Sec-Fetch-User']
        if 'Upgrade-Insecure-Requests' in post_request_headers: del post_request_headers['Upgrade-Insecure-Requests']


        print(f"\nĐang gửi thông tin đăng nhập tới: {post_url}")
        response_post = session.post(post_url, data=payload, headers=post_request_headers, allow_redirects=True, timeout=25) 
        
        print(f"Status Code của POST request: {response_post.status_code}")
        print(f"URL cuối cùng sau redirects (nếu có): {response_post.url}")

        cookies_dict_after_post = session.cookies.get_dict()
        
        if 'c_user' in cookies_dict_after_post and 'xs' in cookies_dict_after_post:
            print("\n>>> Đăng nhập Facebook bằng UID/Pass có vẻ thành công (tìm thấy 'c_user', 'xs')! <<<")
            print(f"  User ID (c_user): {cookies_dict_after_post['c_user']}")
            save_cookies_to_file(session.cookies) 
            return True
        
     
        response_text_lower = response_post.text.lower()
        response_url_lower = response_post.url.lower()

        is_checkpoint_or_2fa = "checkpoint" in response_url_lower or \
                               "checkpoint" in response_text_lower or \
                               "login_approvals" in response_url_lower or \
                               "twofactor" in response_text_lower or \
                               "two_factor" in response_text_lower or \
                               "xác thực 2 yếu tố" in response_text_lower or \
                               "mã xác thực" in response_text_lower

        if is_checkpoint_or_2fa:
            print("\n!!! ĐĂNG NHẬP THẤT BẠI: Tài khoản bị checkpoint hoặc yêu cầu xác thực hai yếu tố (2FA).")
        elif "the password you entered is incorrect" in response_text_lower or \
             "incorrect email/password" in response_text_lower or \
             "sai mật khẩu" in response_text_lower:
             print("\n!!! ĐĂNG NHẬP THẤT BẠI: Sai email hoặc mật khẩu.")
        elif ("www.facebook.com/login/" in response_url_lower or \
              "id=\"login_form\"" in response_text_lower):
             print("\n!!! ĐĂNG NHẬP THẤT BẠI: Có vẻ vẫn ở trang đăng nhập hoặc bị chuyển về trang đăng nhập.")
        else:
   
            print("\nĐăng nhập thất bại không xác định rõ. Dưới đây là một phần phản hồi từ server:")
            print(f"  URL cuối cùng: {response_post.url}") 
            print(response_post.text[:1000]) 

        return False

    except requests.exceptions.Timeout:
        print("Lỗi: Yêu cầu đăng nhập timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Lỗi Request khi đăng nhập: {e}")
        return False
    except Exception as e:
        print(f"Lỗi không xác định trong quá trình đăng nhập UID/Pass: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_cookies_and_session():
    session = requests.Session()
    cookies_dict = {}
    
    while True: 
        print("\nChọn đăng nhập:")
        print("1. Đăng nhập Cookie đã lưu")
        print("2. Xóa/nhập cookie mới")
        print("3. Lấy Cookie bằng uid/pass")
        main_choice = input("Lựa chọn (1, 2, hoặc 3): ").strip()

        if main_choice == '1':
            print("\n--- Đăng nhập Cookie đã lưu ---")
            loaded_cookies = load_cookies_from_file()
            if loaded_cookies and "c_user" in loaded_cookies:
                cookies_dict = loaded_cookies
                session.cookies.update(cookies_dict)
                user_id_val = get_user_id_from_cookies(cookies_dict)
                print(f"Sử dụng cookie đã lưu. User ID: {user_id_val}")
                return session, cookies_dict
            else:
                print("Mày chưa có cookie. Vui lòng chọn 2 hoặc 3.")
                continue

        elif main_choice == '2':
            print("\n--- Xóa/nhập cookie mới ---")
            if os.path.exists("cookie.txt"):
                delete_choice = input("Đã tìm thấy cookie.txt. mày có chắc muốn xóa? (y/n): ").strip().lower()
                if delete_choice == 'y':
                    try:
                        os.remove("cookie.txt")
                        print("Đã xóa file cookie.txt.")
                    except Exception as e:
                        print(f"Lỗi khi xóa cookie.txt: {e}")
            
            print("Vui lòng nhập cookie Facebook mới của bạn:")
            while True: 
                cookie_str = input("Nhập cookie: ").strip()
                if not cookie_str:
                    print("Cookie không được để trống. Vui lòng nhập lại hoặc để trống và nhấn Enter để quay lại menu chính.")
                    empty_confirm = input("Để trống và nhấn Enter để quay lại menu chính: ").strip()
                    if not empty_confirm:
                        break 
                    continue

                temp_cookies = {}
                for item in cookie_str.split(';'):
                    parts = item.strip().split('=', 1)
                    if len(parts) == 2:
                        temp_cookies[parts[0]] = parts[1]
                
                if temp_cookies and "c_user" in temp_cookies:
                    cookies_dict = temp_cookies
                    session.cookies.update(cookies_dict)
                    current_user_id = get_user_id_from_cookies(cookies_dict)
                    if current_user_id:
                        save_cookies_to_file(session.cookies)
                        print(f"Đã lưu cookie mới. User ID: {current_user_id}")
                        return session, cookies_dict
                    else:
                        print("Cookie có vẻ hợp lệ nhưng không lấy được user_id (c_user). Vui lòng kiểm tra lại cookie và nhập lại.")
                        continue 
                else:
                    print("Cookie không hợp lệ. Vui lòng nhập lại.")
                    continue
       
            continue

        elif main_choice == '3':
            print("\n--- Lấy Cookie mới bằng UID/Pass ---")
            uid = input("Nhập UID (Email/SĐT): ").strip()
            pwd = input("Nhập Mật khẩu: ").strip()
            if not uid or not pwd:
                print("UID và Mật khẩu không được để trống.")
                continue

            login_session = requests.Session() 
            print("Đang thử đăng nhập để lấy cookie...")
            if login_via_uid_pass(login_session, uid, pwd):
                cookies_dict = login_session.cookies.get_dict()
                session.cookies.update(cookies_dict)
                current_user_id = get_user_id_from_cookies(cookies_dict)
                if current_user_id:
                    print(f"\nĐăng nhập bằng UID/Pass và lấy cookie thành công! User ID: {current_user_id}")
                    print("Cookie đã được tự động áp dụng cho phiên làm việc này.")
                    return session, cookies_dict
                else:
                    print("\nLấy cookie bằng UID/Pass thành công nhưng không lấy được User ID từ cookie. Vui lòng thử lại.")
            else:
                print("\nLấy cookie bằng UID/Pass thất bại. Vui lòng kiểm tra lại thông tin hoặc thử lại sau.")
            continue 
            
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn 1, 2, hoặc 3.")
            continue 
    
    print("Không thể khởi tạo phiên làm việc. Kết thúc.")
    return None, None

def get_user_id_from_cookies(cookies):
    return cookies.get("c_user")

def get_fb_dtsg(session, user_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Referer": "https://www.facebook.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    }
    try:
        response = session.get("https://www.facebook.com/", headers=headers, timeout=10)
        response.raise_for_status()
        match_json = re.search(r'require\(\s*\[\s*"LSD"\s*\]\s*,\s*function\s*\(a\)\s*\{\s*a\.handle\(([^)]+)\)\);', response.text)
        if match_json:
            try:
                lsd_data = json.loads(match_json.group(1))
                for item in lsd_data:
                    if isinstance(item, dict) and item.get("name") == "fb_dtsg":
                        return item.get("value")
            except json.JSONDecodeError:
                pass
        match_html = re.search(r'name="fb_dtsg" value="([^"]+)"', response.text)
        if match_html:
            return match_html.group(1)
        match_script_token = re.search(r'"token"\s*:\s*"([^"]+)"', response.text)
        if match_script_token:
            fb_dtsg_candidate = match_script_token.group(1)
            if len(fb_dtsg_candidate) > 20:
                return fb_dtsg_candidate
        print("Không tìm thấy fb_dtsg.")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi lấy fb_dtsg: {e}")
    return None

def parse_story_url(story_url):
    parsed_url = urlparse(story_url)
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) >= 3 and path_parts[0] == 'stories':
        return path_parts[1], path_parts[2]
    print(f"Không thể parse author_id và story_card_id từ URL: {story_url}")
    return None, None

def react_to_story(session, user_id, fb_dtsg, author_id, story_card_id, reaction_emoji, author_name, emoji_names_map):
    if not all([user_id, fb_dtsg, author_id, story_card_id, reaction_emoji]):
        return False
    variables = {
        "input": {
            "lightweight_reaction_actions": {
                "offsets": [0],
                "reaction": reaction_emoji
            },
            "story_id": story_card_id,
            "story_reply_type": "LIGHT_WEIGHT",
            "actor_id": user_id,
            "client_mutation_id": 7
        }
    }
    form_data = {
        "av": user_id,
        "__user": user_id,
        "__a": "1",
        "fb_dtsg": fb_dtsg,
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "useStoriesSendReplyMutation",
        "variables": json.dumps(variables),
        "server_timestamps": "true",
        "doc_id": "3769885849805751"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Referer": f"https://www.facebook.com/stories/{author_id}/{story_card_id}",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-FB-Friendly-Name": "useStoriesSendReplyMutation",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    try:
        response = session.post(GRAPHQL_URL, data=form_data, headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("errors"):
            return False
        processed_data = response_data.get("data", {}).get("direct_message_reply", {}).get("story", {})
        reaction_confirmed = False
        try:
            reactions_edges = processed_data.get("story_card_info", {}).get("story_card_reactions", {}).get("edges", [])
            if reactions_edges:
                for edge in reactions_edges:
                    actor_node = edge.get("node", {}).get("messaging_actor", {})
                    if actor_node.get("id") == user_id:
                        user_actions_edges = edge.get("node", {}).get("messaging_actions", {}).get("edges", [])
                        if user_actions_edges:
                            for action_edge in user_actions_edges:
                                action_node = action_edge.get("node", {})
                                if action_node and action_node.get("reaction") == reaction_emoji:
                                    emoji_name = emoji_names_map.get(reaction_emoji, reaction_emoji)
                                    print(f'Đã thả cảm xúc | "{emoji_name}" |cho {author_name} thành công!')
                                    reaction_confirmed = True
                                    break
                        if reaction_confirmed:
                            break
        except Exception:
            pass
        return reaction_confirmed
    except requests.exceptions.RequestException:
        pass
    except json.JSONDecodeError:
        pass
    return False

def fetch_story_tray_data(session, user_id, fb_dtsg):
    if not all([user_id, fb_dtsg]):
        print("Thiếu user_id hoặc fb_dtsg để fetch_story_tray_data.")
        return None
    print("\n--- Đang tìm story ---")
    variables = {
        "bucketsCount": 9,
        "cursor": None,
        "hideSelfBucket": False,
        "pinnedIDs": [""],
        "scale": 1,
        "showNavPane": True,
        "storiesTrayType": "TOP_OF_FEED_TRAY",
        "id": user_id
    }
    doc_id_for_story_tray = "24431142943154549"
    form_data = {
        "av": user_id,
        "__user": user_id,
        "__a": "1",
        "__comet_req": "15",
        "fb_dtsg": fb_dtsg,
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "StoriesTrayQuery",
        "variables": json.dumps(variables),
        "server_timestamps": "true",
        "doc_id": doc_id_for_story_tray
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.facebook.com/stories/",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-FB-Friendly-Name": "StoriesTrayQuery",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    try:
        response = session.post(GRAPHQL_URL, data=form_data, headers=headers, timeout=20)
        response.raise_for_status()
        response_data = response.json()
        return response_data
    except requests.exceptions.HTTPError as e:
        print(f"Lỗi HTTP khi fetch story tray: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi request khi fetch story tray: {e}")
    except json.JSONDecodeError:
        print("Lỗi: Phản hồi không phải là JSON hợp lệ khi fetch story tray.")
    return None

def parse_new_story_data(response_data, current_user_id):
    stories = []
    if not response_data or "data" not in response_data or not isinstance(response_data["data"], dict):
        print("Lỗi: response_data không hợp lệ hoặc thiếu key 'data'.")
        return stories
    node_data = response_data["data"].get("node")
    if not node_data or not isinstance(node_data, dict):
        print("Lỗi: Không tìm thấy 'node' trong response_data['data'].")
        return stories
    unified_stories_buckets = node_data.get("unified_stories_buckets")
    if not unified_stories_buckets or not isinstance(unified_stories_buckets, dict):
        print("Lỗi: Không tìm thấy 'unified_stories_buckets' trong node_data.")
        return stories
    bucket_edges = unified_stories_buckets.get("edges")
    if not isinstance(bucket_edges, list):
        return stories
    for bucket_edge in bucket_edges:
        if not isinstance(bucket_edge, dict): continue
        bucket_node = bucket_edge.get("node")
        if not isinstance(bucket_node, dict): continue
        story_bucket_owner = bucket_node.get("story_bucket_owner")
        if not isinstance(story_bucket_owner, dict): continue
        author_id = story_bucket_owner.get("id")
        author_name = story_bucket_owner.get("name", "Không rõ tên")
        if not author_id or author_id == current_user_id:
            continue
        unified_stories = bucket_node.get("unified_stories")
        if not isinstance(unified_stories, dict): continue
        story_card_edges = unified_stories.get("edges")
        if not isinstance(story_card_edges, list) or not story_card_edges:
            continue
        for story_card_edge in story_card_edges:
            if not isinstance(story_card_edge, dict): continue
            story_card_node = story_card_edge.get("node")
            if not isinstance(story_card_node, dict): continue
            story_card_id = story_card_node.get("id")
            is_seen_by_viewer = story_card_node.get("story_card_seen_state", {}).get("is_seen_by_viewer", False)
            if story_card_id:
                stories.append({
                    "author_id": author_id,
                    "story_card_id": story_card_id,
                    "author_name": author_name,
                    "is_seen": is_seen_by_viewer
                })
    return stories

class SecurityVerifier:
    """Lớp kiểm tra bảo mật"""

    @staticmethod
    def verify() -> bool:
        """
        Xác minh tính hợp lệ của tool

        Returns:
            True nếu hợp lệ, False nếu không
        """
        _author = A_C["AUTHOR"]
        _fb_url = A_C["FACEBOOK_URL"]
        _verification_key = f"{_author}|{_fb_url}"

        _encoded_verification = "==wL0VWe1hGdo5Wak5WYoB3Lt92Yus2bvJWZjFmZuc3d39yL6MHc0RHa8R3v6Gee1hGVggmbsOMkEDibhhGU"

        try:
            reversed_string = _encoded_verification[::-1]
            decoded_bytes = base64.b64decode(reversed_string.encode('utf-8'))
            decoded_string = decoded_bytes.decode('utf-8')

            return decoded_string == _verification_key
        except Exception:

            return False


def story_fb() -> bool:
    print("--- KHỞI TẠO PHIÊN LÀM VIỆC ---")
    session, cookies = get_cookies_and_session()
    if not session or not cookies:
        print("Không thể lấy được thông tin xác thực (session/cookies). Thử lại sau.")
        return False
    user_id = get_user_id_from_cookies(cookies)
    if not user_id:
        print("Không thể lấy User ID từ cookies đã cung cấp/đăng nhập.")
        return False
    fb_dtsg = get_fb_dtsg(session, user_id)
    if not fb_dtsg:
        print("Không thể lấy fb_dtsg. Kiểm tra lại cookie/session hoặc kết nối mạng.")
        return False
    print(f"fb_dtsg: {fb_dtsg}")
    all_custom_emojis = ["💦", "💯", "👽", "👾", "💋"]
    story_tray_response_data = fetch_story_tray_data(session, user_id, fb_dtsg)
    stories_to_react = []
    if story_tray_response_data:
        stories_to_react = parse_new_story_data(story_tray_response_data, user_id)
        if stories_to_react:
            print(f"Đã tìm thấy {len(stories_to_react)} đối tượng khả nghi.")
        else:
            print("Không tìm thấy đối tượng nào.")
    else:
        print("Không nhận được hoặc không parse được dữ liệu JSON từ fetch_story_tray_data.")
    if stories_to_react:
        emojis_to_send = all_custom_emojis
        emoji_names_map = {
            "💦": "Nước mắt",
            "💯": "Một trăm",
            "👽": "Elian",
            "👾": "Rô bốt",
            "💋": "Hôn"
        }
        stories_by_author = defaultdict(list)
        for story_info in stories_to_react:
            stories_by_author[story_info['author_id']].append(story_info)
        ordered_author_ids = []
        seen_author_ids = set()
        for story_info in stories_to_react:
            author_id_val = story_info['author_id']
            if author_id_val not in seen_author_ids:
                ordered_author_ids.append(author_id_val)
                seen_author_ids.add(author_id_val)
        for author_id in ordered_author_ids:
            author_stories = stories_by_author[author_id]
            if not author_stories:
                continue
            author_name = author_stories[0]["author_name"]
            print(f"> Đối tượng: {author_name}")
            for story_info_inner in author_stories:
                current_story_card_id = story_info_inner["story_card_id"]
                for emoji in emojis_to_send:
                    success = react_to_story(session, user_id, fb_dtsg, story_info_inner["author_id"], current_story_card_id, emoji, author_name, emoji_names_map)
                    if not success:
                        emoji_name = emoji_names_map.get(emoji, emoji)
                        print(f'Không thả được cảm xúc "{emoji_name}" cho {author_name}.')
                    time.sleep(1)
    print("\n--- Kịch bản kết thúc ---")
    return True

if __name__ == '__main__':
    if not SecurityVerifier.verify():
        pass 
    else:

        display_banner()
        print("Bắt đầu chương trình...")
        if not story_fb():
            print("\nĐã có lỗi xảy ra hoặc người dùng chọn thoát. Kết thúc chương trình.")
        else:
            print("\nChương trình hoàn tất các tác vụ đã chọn.")
        input("Nhấn Enter để thoát...") 