import json
import math
import re
import sys
import datetime
import jinja2
from iso639 import languages

env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
streamer_info_template = env.get_template("templates/streamer_info_template.html")
gui_template = env.get_template("templates/gui_templete.html")

role_to_ko = {
    "vips": "VIP",
    "moderators": "매니저",
    "staff": "트위치 직원",
    "admins": "트위치 운영자",
    "global_mods": "Global Moderators",
}
history_to_ko = {
    "banned_history": "정지 기록",
    "past_login": "예전 아이디",
    "past_display_name": "예전 이름",
    "past_description": "예전 설명",
}
order_dict = {
    "follow": ["팔로워 많은", "팔로워 적은"],
    "time": ["오래된", "최근"],
    "canceled": ["언팔로우부터", "언팔로우부터"],
}
api_url = "https://woowakgood.live:8007"
home_url = "https://woowakgood.live"
role_to_icon = {
    "moderators": "https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/3",
    "vips": "https://static-cdn.jtvnw.net/badges/v1/b817aba4-fad8-49e2-b88a-7cc744dfa6ec/3",
    "admins": "https://static-cdn.jtvnw.net/badges/v1/9ef7e029-4cdf-4d4d-a0d5-e2b3fb2583fe/3",
    "broadcaster": "https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/3",
    "staff": "https://static-cdn.jtvnw.net/badges/v1/d97c37bd-a6f5-4c38-8f57-4e4bef88af34/3",
    "global_mods": "https://static-cdn.jtvnw.net/badges/v1/9ef7e029-4cdf-4d4d-a0d5-e2b3fb2583fe/3",
}
stream_info_template = env.get_template("templates/stream_info_template.html")
menu_template = env.get_template("templates/menu_template.html")
menus = {
    "stream": ["/twitch/stream", "현재 켜진 방송 및 스트리머들 목록"],
    "watching": ["/twitch/streamer_watching_streamer", "방송 보는 스트리머"],
    "watch": ["/twitch/watching_broadcasts", "스트리머가 보는 방송"],
    "followed": ["/twitch/followed", "스트리머를 팔로우하는 스트리머"],
    "following": ["/twitch/following", "스트리머가 팔로우하는 스트리머"],
    "as_manager": ["/twitch/as_manager", "매니저로 활동하는 방송"],
    "managers": ["/twitch/managers", "매니저 목록"],
    "rank": ["/twitch/rank", "한국 트위치 팔로워 랭킹"],
    "unfollow": ["/twitch/unfollow", "언팔로우 목록"],
    "fired": ["/twitch/fired", "매니저에서 해고당한 스트리머 목록"],
    "banned": ["/twitch/banned", "정지 / 탈퇴한 스트리머들 목록"],
    "history": ["/twitch/history", "과거 아이디 / 이름 / 설명 등등"],
    "contact": ["/contact", "버그 제보 / 기능 제안 / Q&A"],
}
about_invalid = "%s에 해당하는 아이디는 영문자 / 숫자로만 이루어지지 않았기 때문에 적합하지 않습니다."
about_skipped = "%s에 해당하는 스트리머는 이미 데이터 배이스 상에 존재하며, 옵션이 따라 건너뛰었습니다."
about_updated = "%s에 해당하는 스트리머는 이미 데이터 베이스 상에 존재하며, 따라서 이를 업데이트하였습니다."
about_added = "%s에 해당하는 스트리머는 데이터베이스에 새롭게 추가되었습니다."
about_failed = (
    "%s에 해당하는 스트리머는 조회에 실패하였습니다. 트위치로부터 영구 혹은 임시 정지를 받거나 존재하지 않는 아이디가 아닌지 확인해보세요."
)
about_banned = "%s에 해당하는 스트리머는 정지를 받거나, 기존에 정지 상태인 것이 확인되었습니다."
about_follow_skipped = "%s에 해당하는 스트리머는 기존에 팔로워 수 정보가 있어서 건너뛰었습니다."
about_follow_updated = "%s에 해당하는 스트리머는 팔로워 수 정보가 업데이트 되었습니다."
description = {
    "invalid": about_invalid,
    "skipped": about_skipped,
    "updated": about_updated,
    "added": about_added,
    "failed": about_failed,
    "banned": about_banned,
}
follow_description = {
    "follow_skipped": about_follow_skipped,
    "follow_updated": about_follow_updated,
}
langtocountry = {
    "Modern Greek (1453-)": "그리스",
    "Tagalog": "타갈로그어권 (필리핀 등지)",
    "Swedish": "스웨덴어권",
    "Spanish": "스페인어권 (남미, 스페인 등지)",
    "Chinese": "중국",
    "French": "프랑스",
    "Polish": "폴란드",
    "Danish": "덴마크",
    "Hungarian": "헝가리",
    "Romanian": "루마니아",
    "Russian": "러시아",
    "Norwegian": "노르웨이",
    "Japanese": "일본",
    "Italian": "이탈리아",
    "German": "독일",
    "Korean": "한국",
    "Thai": "태국",
    "Czech": "체코",
    "Vietnamese": "베트남",
    "Dutch": "네덜란드",
    "Slovak": "슬로바키아",
    "Catalan": "카탈루냐어권 (유럽 등지)",
    "Ukrainian": "우크라이나",
    "English": "영어권",
    "Indonesian": "인도네시아",
    "Bulgarian": "불가리아",
    "Hindi": "힌디어권 (인도, 네팔 등지)",
    "Malay (macrolanguage)": "말레이어권 (말레이시아, 싱가포르 등지)",
    "Arabic": "아랍어권",
    "other": "기타 국가",
    "Turkish": "튀르키예 (터키)",
    "Portuguese": "포르투갈",
    "Finnish": "핀란드",
}
size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, "__dict__"):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def ends_with_jong(kstr):
    k = kstr[-1]
    if "가" <= k <= "힣":
        return (ord(k) - ord("가")) % 28 > 0
    else:
        return


def eun(kstr):
    josa = "은" if ends_with_jong(kstr) else "는"
    return f"{kstr}{josa}"


def yi(kstr):
    josa = "이" if ends_with_jong(kstr) else "가"
    return f"{kstr}{josa}"


def gwa(kstr):
    josa = "과" if ends_with_jong(kstr) else "와"
    return f"{kstr}{josa}"


def eul(kstr):
    josa = "을" if ends_with_jong(kstr) else "를"
    return f"{kstr}{josa}"


def onlyyi(kstr):
    return "이" if ends_with_jong(kstr) else "가"


def onlyeul(kstr):
    return "을" if ends_with_jong(kstr) else "를"


def onlyeun(kstr):
    return "은" if ends_with_jong(kstr) else "는"


def is_valid_login(login):
    return bool(re.match("^[A-Za-z0-9_-]*$", login)) and login and login[0] != "_"


def clear_name(dirty_name):
    new_name = re.sub("[^A-Za-z가-힣]", "", dirty_name)
    # ''.join([j for j in dirty_name.lower() if not j.isdigit() and not j in ['_', ' ']])
    if new_name:
        return new_name
    else:
        return dirty_name


def now():
    return datetime.datetime.now()


def is_valid_logins(logins):
    for i in logins:
        if not is_valid_login(i):
            return False
    return True


def remove_all(l, x):
    l[:] = list(filter((x).__ne__, l))


def collect_valid_logins(logins):
    valid_logins, invalid_logins = [], []
    for i in logins:
        if is_valid_login(i):
            valid_logins.append(i)
        else:
            invalid_logins.append(i)
    return valid_logins, invalid_logins


def dttoko(ti: datetime.datetime):
    datedifference = (datetime.date.today() - ti.date()).days
    if datedifference < 3:
        datename = ["오늘", "어제", "엊그저께"][datedifference]
    elif datedifference < 10:
        datename = "%d일전" % datedifference
    else:
        datename = str(ti.date())
    ex = "오전"
    ho = ti.hour
    if ti.hour > 12:
        ex = "오후"
        ho = ti.hour - 12
    return "%s %s %d시 %d분" % (datename, ex, ho, ti.minute)


def tdtoko(ti: datetime.timedelta):
    ms, s, d = ti.microseconds, ti.seconds, ti.days

    if d > 365.25:
        return f"{int(d / 365.25)}년"
    if d > 365 / 12:
        return f"{int(d / (365 / 12))}달"
    if d > 0:
        return f"{d}일"
    if s > 3600:
        return f"{int(s / 3600)}시간"
    if s > 60:
        return f"{int(s / 60)}분"
    if s > 0:
        return f"{s}초"
    if ms > 1000:
        return f"{int(ms / 1000)}ms"
    return f"{ms}us"


def passed_time(that_time: datetime.datetime):
    return tdtoko(now() - that_time)


def twitch_parse(t):
    return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(
        hours=9
    )


def timedelta_to_ko(time_delta):
    return "%d 시간 %d 분 %d 초" % (
        time_delta.seconds // 3600,
        (time_delta.seconds // 60) % 60,
        (time_delta.seconds % 60),
    )


def json_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def langcode_to_langname(lang):
    # {'', 'sv', 'th', 'cs', 'vi', 'en', 'el', 'nl', 'ar', 'pl', 'sk', 'es', 'ko', 'uk', 'no', 'ca', 'id', 'ja', 'bg',
    #  'zh-hk', 'da', 'fr', 'hi', 'tl', 'ru', 'hu', 'it', 'ms', 'ro', 'pt', 'asl', 'tr', 'fi', 'other', 'zh', 'de'}

    try:
        return languages.get(alpha2=lang).name
    except:
        return "other"


def langcode_to_country(langcode):
    langname = langcode_to_langname(langcode)
    # other Swedish Thai Czech Vietnamese English Modern Greek (1453-) Dutch Arabic Polish Slovak Spanish Korean Ukrainian Norwegian Catalan Indonesian Japanese Bulgarian other Danish French Hindi Tagalog Russian Hungarian Italian Malay (macrolanguage) Romanian Portuguese other Turkish Finnish other Chinese German
    if langname in langtocountry:
        return langtocountry[langname]
    return langname


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def obj_size_str(obj):
    return convert_size(get_size(obj))


def significant(x, n):
    return formatNumber(round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1)))


def formatNumber(num):
    if num % 1 == 0:
        return int(num)
    else:
        return num


def numtoko(number):
    if number < 10000:
        return str(number)
    if number < 100000000:
        return str(significant(number / 10000, 3)) + "만"
    return str(significant(number / 100000000, 3)) + "억"


def button_templete(link, name, id=""):
    if not id:
        return f"""<div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='location.href="{link}"'>{name}</button></div></div>"""
    else:
        return f"""<div class="col-12 col-md-5 col-xl-3 centering" id="{id}" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='location.href="{link}"'>{name}</button></div></div>"""
