import jinja2

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
order_dict = {"follow": ["팔로워 많은", "팔로워 적은"], "time": ["오래된", "최근"]}
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
