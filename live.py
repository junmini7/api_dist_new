from core import Streamer, D, T
from datetime import datetime as dt
import traceback
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi_utils.tasks import repeat_every
from typing import List, Optional, Tuple, Union
import threading
from threading import Thread
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import subprocess
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    PlainTextResponse,
    FileResponse,
)
import os
import uvicorn
import random
import jinja2
from typing import Tuple, List, Set, Dict
import tools
import itertools
import time
from collections import Counter
import background
import argparse
import sys
import settings

# pop_data = pickle.load(open('pop.pandas', 'rb'))

app = FastAPI()
env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
gui_template = env.get_template("templates/gui_templete.html")
streamer_info_template = env.get_template("templates/streamer_info_template.html")
stream_info_template = env.get_template("templates/stream_info_template.html")
menu_template = env.get_template("templates/menu_template.html")
api_url = "https://woowakgood.live:8007"
home_url = "https://woowakgood.live"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

role_to_icon = {
    "moderators": "https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/3",
    "vips": "https://static-cdn.jtvnw.net/badges/v1/b817aba4-fad8-49e2-b88a-7cc744dfa6ec/3",
    "admins": "https://static-cdn.jtvnw.net/badges/v1/9ef7e029-4cdf-4d4d-a0d5-e2b3fb2583fe/3",
    "broadcaster": "https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/3",
    "staff": "https://static-cdn.jtvnw.net/badges/v1/d97c37bd-a6f5-4c38-8f57-4e4bef88af34/3",
    "global_mods": "https://static-cdn.jtvnw.net/badges/v1/9ef7e029-4cdf-4d4d-a0d5-e2b3fb2583fe/3",
}

search_data = D.streamers_search_data_update()
temp_data = {}
temp_working = {}
bots_list = D.bots_list()
popular_streams = []
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

queues_dict = {
    "follownum": background.follownum_queue,
    "id": background.id_queue,
    "login": background.login_queue,
    "following": background.following_queue,
    "update": background.update_queue,
    "role": background.role_queue,
}

global_variable_dicts = {
    "search data": search_data,
    "temp data for gui ": temp_data,
    "temp working for gui": temp_working,
    "bot list": bots_list,
    "headers": T.header,
    "now working on view": T.now_working_on_view,
    "temp view": T.temp_view,
    "popular streams": popular_streams,
}


@app.middleware("http")
async def logging(request: Request, call_next):
    whattolog = f'{dt.now().strftime("%Y/%m/%d %H:%M:%S")} {str(request.client.host)} {request.method} {request.url.path} {request.path_params} {request.query_params}\n'
    with open("request_log.txt", "a") as f:
        f.write(whattolog)
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        try:
            open("error_log.txt", "a").write(
                whattolog[:-1] + traceback.format_exc() + "\n"
            )
        except:
            open("error_log.txt", "w").write(
                whattolog[:-1] + traceback.format_exc() + "\n"
            )
        # raise HTTPException(status_code=200, detail="error occured, and reported")
        return HTMLResponse(content="서버에 에러가 발생했습니다...", status_code=200)


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(
        "./favicon.ico", media_type="application/octet-stream", filename="favicon.ico"
    )


def mutual_follow_information(
    following_data: dict,
    followed_data: dict,
    broadcaster: Streamer,
    streamer: Streamer,
    follow_crawled: bool,
) -> Tuple[int, str, str]:
    streamer_id = streamer.id
    streamer_login = streamer.login
    broadcaster_login = broadcaster.login
    if not follow_crawled:
        return (
            0,
            "fa-solid fa-question",
            f"<a href='../following/?query={streamer_login}'>확인하기</a>",
        )
    # try:
    #     to_to_from = to_streamer.is_following(from_streamer, False)
    # except FileNotFoundError:
    #     return "fa-solid fa-question", f"<a href='../following/?query={to_streamer.login}'>확인하기</a>"
    if streamer_id in followed_data:
        if streamer_id in following_data:
            return (
                1,
                "fa-solid fa-heart red",
                f"<a href='/twitch/following/?query={streamer_login}'>{followed_data[streamer_id]['when'].date()}</a>",
            )
        else:
            return (
                2,
                "fa-solid fa-heart",
                f"<a href='/twitch/following/?query={streamer_login}'>{followed_data[streamer_id]['when'].date()}</a>",
            )
    else:
        if streamer_id in following_data:
            return (
                3,
                "fa-solid fa-heart green",
                f"<a href='/twitch/following/?query={broadcaster_login}'>{following_data[streamer_id]['when'].date()}</a>",
            )
        else:
            return (
                4,
                "fa-regular fa-heart",
                f"<a href='/twitch/following/?query={streamer_login}&refresh=True'>새로고침</a>",
            )


def streamer_info_maker(
    streamer: Streamer,
    broadcaster: Streamer,
    now: dt,
    following_data: dict,
    followed_data: dict,
    role_data: dict,
    follow_crawled: bool,
) -> dict:
    mutual_info = mutual_follow_information(
        following_data, followed_data, broadcaster, streamer, follow_crawled
    )
    if streamer.id in role_data:
        role = role_data[streamer.id]["role"]
        role_icon = f'<img src="{role_to_icon[role]}" width="15" height="15"/>'
    else:
        role = ""
        role_icon = ""
    followers = streamer.followers
    rendered = streamer_info_template.render(
        login=streamer.login,
        image_url=streamer.profile_image,
        name=streamer.name,
        follower=tools.numtoko(followers),
        country=streamer.country,
        rank=streamer.localrank,
        time=tools.tdtoko(now - streamer.last_updated),
        icon=mutual_info[1],
        following=mutual_info[2],
        api_url=api_url,
        login_disp=streamer.login != streamer.name.lower(),
        role_icon=role_icon,
    )

    # role_info = D.role_check(broadcaster.id, streamer.id)
    # if streamer.followers==-1:
    #     return streamer_info_template.render(login=streamer.login, image_url=streamer.profile_image, name=streamer.name,
    #                                      follower="?", country=streamer.country,
    #                                      rank="?", time="?",
    #                                      icon=mutual_info[0],
    #                                      following=mutual_info[1], api_url=api_url,
    #                                      login_disp=streamer.login != streamer.name.lower(),
    #                                      is_manager=D.role_check(broadcaster.id, streamer.id))
    return {
        "mutual": mutual_info,
        "role": role,
        "rendered": rendered,
        "followers": followers,
        "login": streamer.login,
    }


def button_templete(link, name, id=""):
    if not id:
        return f"""<div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='location.href="{link}"'>{name}</button></div></div>"""
    else:
        return f"""<div class="col-12 col-md-5 col-xl-3 centering" id="{id}" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='location.href="{link}"'>{name}</button></div></div>"""


def streamers_search_recommend_client(query):
    result = D.streamers_data_name_search(query, search_data)
    temp = f"<meta charset='utf-8'>'{query}'에 해당하는 스트리머가 없습니다. 스트리머의 이름 또는 아이디 둘 다로 검색 가능하니 다시 한번 해보세요. "
    if len(result) == 1:
        temp += f"<br><a href='/twitch/streamer_watching_streamer/?query={result[0]}'>{result[0]}</a>가 찾고 계신 스트리머 인가요? 만약 그렇다면 링크를 누르세요."
    elif len(result) > 1:
        temp += f"<br>혹시 {', '.join([f'''<a href='/twitch/streamer_watching_streamer/?query={rec}'>{rec}</a>''' for rec in result])} 중에 찾고 계신 스트리머가 있나요? "
    return temp


def query_parser(query):  # -> Tuple[str, Streamer | str]:
    broadcaster = D.streamers_search(query)
    if not broadcaster:
        return "invalid", streamers_search_recommend_client(query)
    if broadcaster.followers == -1:
        try:
            broadcaster.update_followers_num()
        except KeyError:
            broadcaster.update_itself()
    if broadcaster.banned:
        broadcaster.update_itself()
        if broadcaster.banned:
            return (
                "banned",
                f"스트리머 {broadcaster.name}({broadcaster.login})는 {broadcaster.banned_history[-1]} 기준으로 정지된 것을 확인했습니다. ",
            )
        # 이렇게 리턴하는 이유는 어차피 지금 확인하고자 하는 특성이 ban 상태에서는 확인불가이기 때문임
    return "active", broadcaster


@app.get("/twitch/populariswatchingapi/", response_class=HTMLResponse)
def watching_streamers_gui(
    request: Request, query: str, follower_requirements: Optional[int] = 100
):
    ip = str(request.client.host)
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    # without_followers = [streamer for streamer in list(itertools.chain.from_iterable(list(watchers.values()))) if
    #                      'followers' not in streamer]
    # if without_followers:
    #     Thread(target=D.get_follower_from_streamers, args=(without_followers, False)).start()
    # log 추가
    watching_streamers_daemon(broadcaster)
    return watching_streamers_maker(broadcaster, follower_requirements)


# f"<div class='row col-12 col-md-11 centering centering_text gx-5'>{} {}</div><br>"


def watching_streamers_daemon(
    broadcaster: Streamer, allow_maximum=settings.allow_maximum_default, refresh_maximum=settings.refresh_maximum_default, wait_while_doing=settings.wait_while_doing_default
):
    if broadcaster.id in temp_data:
        time_elapsed = tools.now() - temp_data[broadcaster.id]["time"]
        if time_elapsed.seconds < allow_maximum:
            if time_elapsed.seconds > refresh_maximum:
                if (
                    broadcaster.id not in temp_working
                    or not temp_working[broadcaster.id]
                ):
                    Thread(
                        target=watching_streamers_worker, args=(broadcaster,)
                    ).start()
                    # print(f'reserved work for {broadcaster}')
                # else:
                # print(f'already working on {broadcaster}')
            # print(f'using result of {broadcaster} on {temp_data[broadcaster.id]["time"]}')
            return False
    if broadcaster.id in temp_working and temp_working[broadcaster.id]:
        start_time = time.time()
        while temp_working[broadcaster.id]:
            time.sleep(1)
            if time.time() - start_time > wait_while_doing:
                open("watching_streamer_error.txt", "a").write(
                    f"{Streamer} {allow_maximum} {refresh_maximum} {wait_while_doing}\n"
                )
                watching_streamers_worker(broadcaster)
                break
                # assert broadcaster.id not in temp_working
        return True
    watching_streamers_worker(broadcaster)
    return True


def watching_streamers_maker(broadcaster: Streamer, follower_requirements: int):
    start_time = time.time()
    assert broadcaster.id in temp_data

    data = temp_data[broadcaster.id]
    temp = data["head"] % follower_requirements
    streamer_temp_data = [
        i
        for i in data["datas"]
        if i["followers"] >= max(follower_requirements, 10) or i["role"]
    ]

    updated = data["time"]
    buttons = data["buttons"][:]
    mutual_infos = dict(Counter([i["mutual"][1] for i in streamer_temp_data]))
    mutual_infos_gui = ", ".join(
        [f'<i class="{k}"></i> : {v}' for k, v in mutual_infos.items()]
    )
    role_infos = dict(Counter([i["role"] for i in streamer_temp_data if i["role"]]))
    role_infos_gui = ", ".join(
        [f"{role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
    )

    if not streamer_temp_data:
        temp += "가 없습니다.<br><br>"
    else:
        if role_infos_gui:
            temp += f"는 총 {len(streamer_temp_data)}명이며, 그 중 {role_infos_gui}입니다."
        else:
            temp += f"는 총 {len(streamer_temp_data)}명입니다."
        if mutual_infos_gui:
            temp += "<br>" + mutual_infos_gui
        temp += '<br><br><div class="row" style="margin-left:4px; margin-right:2px;">'
        temp += "".join([i["rendered"] for i in streamer_temp_data])
        temp += "</div>"
        buttons.append(
            button_templete(
                f"{api_url}/twitch/addlogin/?logins={broadcaster.login}&{'&'.join(['logins=' + k['login'] for k in streamer_temp_data])}&skip_already_done=false&give_chance_to_hakko=true",
                "팔로워 수 업데이트 (오래 걸림)</button>",
                "update_follow",
            )
        )

    temp += f"""<br><div class='row col-12 col-md-11 centering centering_text gx-5'>{''.join(buttons)}</div><br>"""  # row col-12 col-md-11 centering centering_text
    temp += f"""
        <div id='description'>
    <div class='row gy-5 centering'>
      <a class="btn col-12 col-lg-3 centering" data-bs-toggle="collapse" href="#legend" role="button" aria-expanded="false" aria-controls="legend">
        팔로우 관련 범례
      </a>
        <a class="btn col-12 col-lg-3 centering" data-bs-toggle="collapse" href="#notice" role="button" aria-expanded="false" aria-controls="notice">
        주의사항
      </a>
      </div>
    <div class='row gy-3 centering'>
    <div class='col-12 col-lg-6'>
    <div class="collapse" id="legend">
      <div class="card card-body">
        <p><i class='fa-solid fa-heart red'></i> : {tools.gwa(broadcaster.name)} 해당 스트리머가 상호 팔로우</p>
        <p><i class='fa-solid fa-heart'></i> : 해당 스트리머만 {tools.eul(broadcaster.name)} 팔로우</p>
        <p><i class='fa-solid fa-heart green'></i> : {broadcaster.name}만 해당 스트리머를 팔로우</p>
        <p><i class='fa-regular fa-heart'></i> : 서로 팔로우 하지 않음</p>
        <p><i class='fa-solid fa-question'></i> : 팔로우 목록을 아직 조사하지 않음</p>
        <p> 날짜는 각 스트리머가 {tools.eul(broadcaster.name)} 팔로우한 일시입니다.</p>
        </div>
    </div>
    </div>
    <div class='col-12 col-lg-6'>
    <div class="collapse" id="notice">
      <div class="card card-body">
     <p>시청 정보 최종 업데이트 일시 : {updated.strftime('%Y/%m/%d, %H:%M:%S')} / {broadcaster.name}의 최종 업데이트 일시 : {broadcaster.last_updated.strftime('%m/%d/%Y, %H:%M:%S')}</p>
     <p>스트리머의 이름이나 프로필 사진을 클릭하면 그 스트리머가 보고 있는 방송을 알 수 있습니다. 물론 모든 방송에 해당되는 것은 아니고 {settings.viewer_minimum}명 이상의 시청자를 가진 최대 {settings.popular_count}개의 방송에서만 해당됩니다.</p>
     <p><a href='https://woowakgood.live:8007/twitch/stats'>데이터베이스 통계 보기</a></p>
    <p>여기에는 없지만 알고 있는 스트리머가 있다면 위에서 검색해보세요. 검색 즉시 자동으로 추가됩니다.</p>
    <p>정지당한 스트리머들은 표시되지 않습니다. <a href='/twitch/banned'>여기서 그 목록을 확인하세요.</a></p>
    <p>순위 옆에 표시되는 시간은 마지막으로 팔로워 수가 업데이트 된 시간을 의미합니다.</p>
    <p>각 링크들을 누르면 해당하는 항목이 새로고침됩니다.</p>
    <p>트위치 채팅창 옆에서 볼 수 있는 참여자 목록에 '커뮤니티의 일부 구성원만 이곳에 나열됩니다.'라고 적혀 있는 것처럼, 트위치 웹사이트에서는 더 이상 전체 시청자 목록을 제공하지 않고 수천명의 시청자 목록 중 몇백명만 랜덤 추출해서 보여 주고 있기 때문에 이 사이트에서 시청 중이라고 표시되더라도 트위치에서는 나오지 않습니다. (이 사이트는 트위치의 별도 개발자 API를 이용하였습니다.)</p>
    <p>한달에 3000원짜리 엄청 느린 저가형 서버라 온갖 방식을 사용해서 적은 시간 복잡도와 공간 복잡도를 가지도록 만들었습니다. 그래서 기능을 하나 추가할 때마다 지켜보면서 최적화하는데 몇 시간에서 며칠 정도 걸립니다.</p>
    <p>다크 모드를 전환하려면 컴퓨터나 핸드폰 자체 설정의 다크 모드 설정을 변경해주세요. <font size="1em">다크모드 컬러 개잘잡았다 ㅇㅈ? ㅇㅇㅈ</font></p>

        </div>
    </div>
    </div>
    </div>
    """
    print(
        f"watching_streamers_maker took {time.time() - start_time}s for {broadcaster.name}"
    )
    return temp


def watching_streamers_worker(broadcaster: Streamer):
    now = tools.now()
    temp_working[broadcaster.id] = True
    # broadcaster.refresh_followers_num()
    background.update_queue.append(broadcaster)
    watchers = broadcaster.watching_streamers()
    start_time = time.time()
    background.update_queue.extend(watchers["viewers"])
    viewers_id = [i.id for i in watchers["viewers"]]
    following_data = {i["to_id"]: i for i in broadcaster.follow_from()}
    assert broadcaster.followers >= 0
    assert broadcaster.localrank
    followed_data = {i["from_id"]: i for i in broadcaster.follow_to()}
    role_data = {i["member_id"]: i for i in broadcaster.role_broadcaster(True, False)}
    role_crawled_watchers_ids = [
        j["id"] for j in D.db.role_data_information.find({"id": {"$in": viewers_id}})
    ]
    follow_crawled_watchers_ids = [
        j["id"] for j in D.db.follow_data_information.find({"id": {"$in": viewers_id}})
    ]
    for streamer in watchers["viewers"]:
        if streamer.followers > 1000:
            if streamer.id not in follow_crawled_watchers_ids:
                background.following_queue.append(streamer)
            if streamer.id not in role_crawled_watchers_ids:
                background.role_queue.append(streamer)
    head = ""
    if watchers["broadcaster"]:
        head += f'{broadcaster.name}({broadcaster.login}) 현재 Broadcaster 접속중 <a href="https://twitch.tv/{broadcaster.login}"><img src="https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/3" width="15" height="15"/></a><br>'
    head += f"{broadcaster.introduce}{tools.onlyeul(broadcaster.name)} 지금 시청 중인 {watchers['count']}명의 로그인 시청자 중 팔로워 수 %d명 이상의 스트리머"
    buttons = [
        """<div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
            <button class='btn btn-primary' onclick='copyToClipboard(window.location.href)'>결과 링크 복사</button></div></div>""",
        button_templete(
            f"/twitch/following?query={broadcaster.login}",
            f"{tools.yi(broadcaster.name)} 팔로우하는 스트리머",
        ),
        button_templete(
            f"/twitch/followed?query={broadcaster.login}",
            f"{tools.eul(broadcaster.name)} 팔로우하는 스트리머",
        ),
        button_templete(
            f"/twitch/managers?query={broadcaster.login}", f"{broadcaster.name}의 매니저 목록"
        ),
        button_templete(
            f"/twitch/as_manager?query={broadcaster.login}",
            f"{tools.yi(broadcaster.name)} 매니저인 방송",
        ),
        button_templete(
            f"/twitch/history?query={broadcaster.login}",
            f"{broadcaster.name}의 과거 아이디 및 이름들",
        ),
        button_templete(
            "/twitch/watching_broadcasts?query=" + broadcaster.login,
            broadcaster.name + "이 보는 방송",
        ),
    ]
    streamer_temp_data = []

    for streamer in watchers["viewers"]:
        if (
            streamer.login not in bots_list
            and not streamer.banned
            and "localrank" in streamer
        ):
            streamer_temp_data.append(
                streamer_info_maker(
                    streamer,
                    broadcaster,
                    now,
                    following_data,
                    followed_data,
                    role_data,
                    streamer.id in follow_crawled_watchers_ids,
                )
            )
    # for role in watchers['managers']:
    #     for streamer in watchers['managers'][role]:
    #         if streamer.login not in bots_list:
    #             streamer_temp_data.append(
    #                 streamer_info_maker(streamer, broadcaster, now, following_data, followed_data, role))
    streamer_temp_data.sort(key=lambda x: x["followers"], reverse=True)
    temp_data[broadcaster.id] = {
        "time": now,
        "head": head,
        "datas": streamer_temp_data,
        "buttons": buttons,
    }
    print(
        f"watching_streamers_worker took {time.time() - start_time}s for {broadcaster.name}"
    )
    temp_working[broadcaster.id] = False


@app.get("/twitch/watchingbroadcasts", response_class=HTMLResponse)
def watching_broadcasts(request: Request, query: str, tolerance: Optional[int] = settings.tolerance_for_watching_broadcasts):
    ip = str(request.client.host)
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    # following_data = {i['to_id']: i for i in broadcaster.follow_from()}
    # followed_data = {i['from_id']: i for i in broadcaster.follow_to()}
    known_logins = []
    watching_logins = []
    for login in list(T.temp_view):
        if (tools.now() - T.temp_view[login]["time"]).seconds <= tolerance:
            known_logins.append(login)
            if broadcaster.login in T.temp_view[login]["view"]["viewers"]:
                watching_logins.append(login)
    if known_logins:
        result = f"현재 시청 목록이 조사된 방송은 {len(known_logins)}개입니다. 그 중 {broadcaster.introduce}가 보고 있는 방송은 "
        if watching_logins:
            result += f'다음과 같습니다. <br><div class="row" style="margin-left:4px; margin-right:2px;">{"".join([D.streamers_search(i).introduce_html for i in watching_logins])}</div>'
        else:
            result += "없습니다."
    else:
        result = "시청목록이 아예 없습니다 죄송합니당"
    return (
        result
        + """<div class='row col-12 col-md-11 centering centering_text gx-5'><div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
            <button class='btn btn-primary' onclick='copyToClipboard(window.location.href)'>결과 링크 복사</button></div></div></div>"""
    )


@app.get("/twitch/populariswatchingapi/{query}", response_class=HTMLResponse)
def please_reload(response_class=HTMLResponse):
    return "please reload"


@app.get("/twitch/populariswatching/")
async def popular_is_watching_introduce(request: Request):
    return RedirectResponse(
        "https://woowakgood.live/twitch/streamer_watching_streamer/"
    )


@app.get("/twitch/populariswatching/{query}")
async def popular_is_watching(request: Request, query: str):
    return RedirectResponse(
        f"https://woowakgood.live/twitch/streamer_watching_streamer?query={query}"
    )


@app.get("/loading.gif")
async def loadinggif():
    return RedirectResponse(
        "https://woowakgood.live/loading-2.gif"
    )  # FileResponse('loading.gif', media_type='application/octet-stream', filename='loading.gif')


@app.get("/twitch/managers/{query}", response_class=HTMLResponse)
async def managers(request: Request, query: str, refresh: Optional[bool] = False):
    parse_result = query_parser(query)
    if parse_result[0] == "banned":
        return parse_result[1]
    broadcaster = parse_result[1]
    managers_data_processed = D.role_data_to_streamers(
        broadcaster.role_broadcaster(False, refresh), "broadcaster"
    )
    manager_streamers = managers_data_processed["datas"]
    total_manager = managers_data_processed["total"]
    background.processed_putter(managers_data_processed)
    # managers_data=broadcaster.role_broadcaster(False)
    # managers_infos = {i['id']: Streamer(i) for i in D.db.streamers_data.find(
    #     {'id': {'$in': [i[f"member_id"] for i in managers_data]}})}
    role_infos = dict(Counter([i["role"] for i in manager_streamers if i["valid"]]))
    role_infos_gui = ", ".join(
        [f"{role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
    )
    return (
        f'<meta charset="utf-8">{broadcaster.introduce} 방송에서 활동하는 매니저 혹은 VIP, 스태프들은 총 {total_manager}명 이며, 각각 {role_infos_gui}입니다. <br>'
        + "<br>".join(
            [
                f"""<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {inf['streamer'].followers}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {broadcaster.name}의 방송에서 {role_to_ko[inf['role']]} {f'을 했었고 현재는 해고당함' if not inf['valid'] else ''}"""
                for inf in manager_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/as_manager/{query}", response_class=HTMLResponse)
async def as_manager(request: Request, query: str, refresh: Optional[bool] = True):
    parse_result = query_parser(query)
    if parse_result[0] == "banned":
        return parse_result[1]
    broadcaster = parse_result[1]
    managers_data_processed = D.role_data_to_streamers(
        broadcaster.role_member(False), "member"
    )
    manager_streamers = managers_data_processed["datas"]
    total_manager = managers_data_processed["total"]
    role_infos = dict(Counter([i["role"] for i in manager_streamers if i["valid"]]))
    role_infos_gui = ", ".join(
        [f"{role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
    )

    return (
        f'<meta charset="utf-8">{broadcaster.introduce}가 매니저 혹은 VIP, 스태프로 활동하는 방송들은 총 {total_manager}개 이며, 각각 {role_infos_gui}입니다. <br>'
        + "<br>".join(
            [
                f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {tools.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {tools.yi(broadcaster.name)} 이 방송에서 {role_to_ko[inf['role']]} {'을 했었고 현재는 해고당함' if not inf['valid'] else ''}"
                # , {inf['last_updated']}에 마지막으로 확인
                for inf in manager_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/following/{query}", response_class=HTMLResponse)
def following_by_popular(
    request: Request,
    query: str,
    by: Optional[str] = "time",
    reverse: Optional[bool] = False,
    refresh: Optional[bool] = False,
    valid: Optional[bool] = True,
):
    parse_result = query_parser(query)
    if parse_result[0] == "banned":
        return parse_result[1]
    broadcaster = parse_result[1]
    # 기존에 팔로우에서 나온 id를 모듈 측에서 업데이트 하려고 했지만 그걸 굳이 비실시간 모듈에서 하기 보다는 실시간 모듈에서 호출할때 해주는게 맞다.
    follow_datas_processed = D.follow_data_to_streamers(
        broadcaster.follow_from(refresh, valid), "from", by, reverse
    )
    following_streamers = follow_datas_processed["datas"]
    total_follow = follow_datas_processed["total"]
    background.processed_putter(follow_datas_processed)
    # Thread(target=D.get_follower_from_streamers, args=(to_streamers, False)).start()
    return (
        f'<meta charset="utf-8">{broadcaster.introduce}가 팔로우하는 스트리머들은 총 {total_follow}명입니다. ({order_dict[by][reverse]} 순)<br>'
        + (
            f"여기 안보이는 {total_follow - len(following_streamers)}명의 스트리머는 정지당하거나, 현재 업데이트 중이기 때문에 볼 수 없습니다.<br>"
            if total_follow - len(following_streamers) != 0
            else ""
        )
        + "<br>".join(
            [
                f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {tools.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {tools.yi(broadcaster.name)} {inf['when']}에 팔로우, {inf['last_updated']}에 마지막으로 확인"
                if inf["valid"]
                else f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {tools.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {tools.yi(broadcaster.name)} {inf['when']}에 팔로우, 및 {inf['last_updated']}에 팔로우 취소한 것 확인 (확인한 시점)"
                for inf in following_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/followedbypopular/{query}", response_class=HTMLResponse)
def followed_by_popular(
    request: Request,
    query: str,
    by: Optional[str] = "time",
    reverse: Optional[bool] = False,
    follower_requirements: Optional[int] = 3000,
    valid: Optional[bool] = True,
):
    parse_result = query_parser(query)
    if parse_result[0] == "banned":
        return parse_result[1]
    broadcaster = parse_result[1]
    followed_streamers_processed = D.follow_data_to_streamers(
        broadcaster.follow_to(valid), "to", by, reverse, max(follower_requirements, 10)
    )
    following_streamers = followed_streamers_processed["datas"]
    total_follow = followed_streamers_processed["total"]
    # from_ids = [i['from_id'] for i in list(D.follow(broadcaster.id, 'to'))]
    # from_streamers = D.streamers_datas('id', from_ids, False)

    # 어차피 이미 다 되있을거라서 할필요 없음
    # for i in from_streamers:
    #     follownum_queue.append(i)
    # Thread(target=D.get_follower_from_streamers, args=(from_streamers, False)).start()

    return (
        f'<meta charset="utf-8">{broadcaster.introduce}를 팔로우하는 {follower_requirements}명 이상의 팔로워를 가진 스트리머는 {total_follow}명입니다. ({order_dict[by][reverse]} 순)<br>'
        + "<br>".join(
            [
                f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {tools.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {tools.eul(broadcaster.name)} {inf['when']}에 팔로우, {inf['last_updated']}에 마지막으로 확인"
                if inf["valid"]
                else f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {tools.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {tools.eul(broadcaster.name)} {inf['when']}에 팔로우, 및 {inf['last_updated']}에 팔로우 취소한 것 확인 (확인한 시점)"
                for inf in following_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/relationship/", response_class=HTMLResponse)
async def relationship(logins: List[str] = Query(None)):
    raise NotImplementedError


@app.get("/twitch/ranking/", response_class=HTMLResponse)
def ranking(request: Request, lang: Optional[str] = "ko", num: Optional[int] = 5000):
    ranking_datas = list(D.streamers_data_ranking(num, lang))
    return (
        f'<meta charset="utf-8">{tools.langcode_to_country(lang)} 내 팔로워 랭킹<br>'
        + f'트위치에서 정지당한 스트리머는 본 목록에 뜨지 않으므로 다음을 참조하세요. <a href="/twitch/banned">정지당한 스트리머 목록</a><br>'
        + "<br>".join(
            [
                f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={v['login']}'><img src='{v['profile_image_url']}' width='100' height='100'></a> {v['display_name']} ({v['login']}), 팔로워 {v['followers']}명, {tools.langcode_to_country(v['lang'])} {v['localrank']}위 (last update on {v['last_updated']})"
                for v in ranking_datas
            ]
        )
    )


@app.get("/twitch/banned/", response_class=HTMLResponse)
async def banned_ui(request: Request, lang: Optional[str] = "ko"):
    banned_list = list(D.currently_banned())
    return (
        f'<meta charset="utf-8">현재 트위치에서 정지당한 스트리머들 목록<br>'
        + "<br>".join(
            [
                f"<a href='{home_url}/twitch/streamer_watching_streamer/?query={v['login']}'><img src='{v['profile_image_url']}' width='100' height='100'></a> {v['display_name']} ({v['login']}) ({tools.tdtoko(dt.now() - v['banned_history'][-1])}전에 마지막으로 밴먹은것 확인) {'팔로워 %d명, %s, %s전에 마지막으로 확인' % (v['followers'], str(v['localrank']), tools.tdtoko(dt.now() - v['last_updated'])) if 'followers' in v and 'localrank' in v else ''}"
                for v in banned_list
            ]
        )
        + f"<br><a href='{api_url}/twitch/addlogin/?{'&'.join(['logins=' + k['login'] for k in banned_list])}&skip_already_done=false&give_chance_to_banned=true'>여기 등장하는 {len(banned_list)}명의 정지당한 스트리머들 새로고침하기"
    )


# @app.get("/twitch/viewerintersection")
# async def viewerintersection(request: Request, streamers: List[str] = Query(None)):
#     ip = str(request.client.host)
#     intersect = D.viewer_intersection(streamers)
#     with open('log.txt', 'a') as f:
#         f.write(
#             f'{dt.now().strftime("%Y/%m/%d %H:%M:%S")} viewerintersection {" ".join(streamers)} from {ip} {" ".join(map(str, intersect))}\n')
#     return intersect


@app.get("/twitch/streams", response_class=HTMLResponse)
async def streams(request: Request, number: Optional[int] = 4):
    result = ""
    for j, i in enumerate(popular_streams):
        streamer = i[0]
        stream = i[1]
        thumb_url = (
            stream["thumbnail_url"]
            .replace("{width}", "1280")
            .replace("{height}", "720")
        )
        viewer_count = tools.numtoko(stream["viewer_count"])
        follower = tools.numtoko(streamer.followers)
        # uptime = tools.tdtoko(stream['uptime'])
        stream_country = "한국"
        stream_rank = j + 1
        if streamer.id in temp_data:
            # crawled_time = str(temp_data[streamer.id]['time'])
            viewer_data = "".join(
                [i["rendered"] for i in temp_data[streamer.id]["datas"][:number]]
            )
            result += stream_info_template.render(
                thumb_url=thumb_url,
                login=streamer.login,
                title=stream["title"],
                viewer_count=viewer_count,
                follower=follower,
                profile_image=streamer.profile_image,
                country=streamer.country,
                rank=streamer.localrank,
                stream_country=stream_country,
                stream_rank=stream_rank,
                name=streamer.name,
                login_disp=streamer.login != streamer.name.lower(),
                crawled=True,
                viewer_data=viewer_data,
            )

        else:
            result += stream_info_template.render(
                thumb_url=thumb_url,
                login=streamer.login,
                title=stream["title"],
                viewer_count=viewer_count,
                follower=follower,
                profile_image=streamer.profile_image,
                country=streamer.country,
                rank=streamer.localrank,
                stream_country=stream_country,
                stream_rank=stream_rank,
                name=streamer.name,
                login_disp=streamer.login != streamer.name.lower(),
                crawled=False,
            )

    return result


@app.get("/twitch/multipleiswatching")
async def multipleiswatching(
    request: Request, streamer: str, ids: List[str] = Query(None)
):
    ip = str(request.client.host)
    peop = T.view(streamer)
    result = list(set(peop) & set(ids))
    with open("log.txt", "a") as f:
        f.write(
            f'{dt.now().strftime("%Y/%m/%d %H:%M:%S")} multiple {" ".join(ids)} iswatching {streamer} from {ip} {" ".join(map(str, result))}\n'
        )

    return result


def streamers_data_update_to_ko(result, follow_result):
    explanation = "<meta charset='utf-8'> 데이터베이스 추가/업데이트 작업이 완료되었습니다."
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
    # about_new_hakko = f"%s에 해당하는 스트리머는 {follower_requirements}명 미만의 팔로워를 보유하고 있기 때문에 데이터 베이스 상에 추가는 되었지만, 앞으로의 통계에 활용되지는 않습니다. {follower_requirements}명의 이상의 팔로워를 가지게 된다면 다시 시도해주세요."
    # about_still_hakko = f"%s에 해당하는 스트리머는 여전히 {follower_requirements}명 미만의 팔로워를 보유하고 있음이 확인되었습니다. {follower_requirements}명의 이상의 팔로워를 가지게 된다면 다시 시도해주세요."
    # about_hakko_to_streamers = f"%s에 해당하는 스트리머는 최근 {follower_requirements}명 이상의 팔로워 기록을 갱신하였기 때문에 기존의 보관용 데이터베이스에서 통계용 데이터베이스로 이동되었습니다. 축하드립니다."
    # about_streamer_to_hakko = f"%s에 해당하는 스트리머는 최근 {follower_requirements}명 미만의 팔로워로 떨어졌기 때문에 기존의 통계용 데이터베이스에서 보관용 데이터베이스로 이동되었습니다."
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

    for i in description:
        if result[i]:
            explanation += "<br>" + description[i] % (
                ", ".join([str(j) for j in result[i]])
            )
    for i in follow_description:
        if follow_result[i]:
            explanation += "<br>" + follow_description[i] % (
                ", ".join([str(j) for j in follow_result[i]])
            )
    return explanation


@app.get("/twitch/addlogin/", response_class=HTMLResponse)
def add_logins(
    request: Request,
    logins: List[str] = Query(None),
    skip: Optional[bool] = False,
    update_follow: Optional[bool] = True,
    follower_requirements: Optional[int] = 3000,
):
    if not tools.is_valid_logins(logins):
        return "make sure if the ID is made up of only alphabets, numbers and under bar"
    background.login_queue.extend(logins)
    update_result = D.update_from_login(logins, skip)
    follow_update_result = D.get_follower_from_streamers(
        update_result["data"], update_follow
    )
    return streamers_data_update_to_ko(update_result, follow_update_result)


@app.get("/twitch/history/{query}", response_class=HTMLResponse)
def past_logins(request: Request, query: str):
    parse_result = query_parser(query)
    if parse_result[0] == "banned":
        return parse_result[1]
    broadcaster = parse_result[1]
    result = {}
    for i in ["banned_history", "past_login", "past_display_name", "past_description"]:
        if i in broadcaster:
            result[i] = broadcaster[i]
    if not result:
        return f"{broadcaster.introduce}는 과거 기록이 없습니다."
    return f"{broadcaster.introduce}의 {', '.join([f'{tools.eun(history_to_ko[k])} {v}' for k, v in result.items()])}<br>(11월 전에는 아이디만 바뀌어도 정지되었다고 판단하는 바람에 그 당시의 정지기록은 의미가 없습니다.)"


@app.get("/twitch/stats", response_class=HTMLResponse)
def statistics():
    return (
        f"전체 스트리머 수 {D.db.streamers_data.count_documents({})}<br>"
        f"팔로워 수 정보가 있는 스트리머 수 {D.db.streamers_data.count_documents({'followers': {'$exists': True}})}<br>"
        f"팔로잉 수 정보가 있는 스트리머 수 {D.db.follow_data_information.count_documents({})}<br>"
        f"팔로워 관계 수 {D.db.follow_data.count_documents({})}<br>"
        f"한국 스트리머 수 {D.db.streamers_data.count_documents({'lang': 'ko'})}<br>"
        f"로컬 랭크가 있는 스트리머 수 {D.db.streamers_data.count_documents({'localrank': {'$exists': True}})}<br>"
        f"글로벌 랭크가 있는 스트리머 수 {D.db.streamers_data.count_documents({'globalrank': {'$exists': True}})}<br>"
        f"밴 당한 스트리머 수 {D.db.streamers_data.count_documents({'banned': True})}<br>"
        f"매니저 정보가 있는 스트리머 수 {D.db.role_data_information.count_documents({})}<br>"
        f"매니저 관계 수 {D.db.role_data.count_documents({})}<br>"
    )


# @app.get("/threadnum", response_class=HTMLResponse)
# def thread_num():
#     return threading.active_count()


@app.get("/twitch/queue", response_class=HTMLResponse)
def queuenum():
    return "<br>".join([f"{i}:{len(j)}" for i, j in queues_dict.items()])


@app.get("/twitch/memory", response_class=HTMLResponse)
def memory():
    return "<br>".join(
        [f"{i}:{tools.obj_size_str(j)}" for i, j in global_variable_dicts.items()]
    )


@app.get("/twitch/thread_manage", response_class=HTMLResponse)
def thread_manager(name: str, num: int):
    background.thread_num_manager(name, num)
    return background.thread_status()


@app.get("/twitch/thread_status", response_class=HTMLResponse)
def background_stats():
    return background.thread_status()


@app.on_event("startup")
@repeat_every(seconds=60)
def refresh_popular_streams() -> None:
    res = D.stream_data_to_streamers(T.streams_info(settings.popular_count, "ko"))
    datas = res["datas"]
    failed = res["failed_ids"]
    background.id_queue.extend(failed)
    popular_streams[:] = [
        i for i in datas if i[1]["viewer_count"] > settings.viewer_minimum
    ]


# 헷갈린 이유가, 이거의 목적이 첫번째는 100명 크롤링해서 보는 사람 알려주는거고 두번째는 쫙 목록 보여주는거
# 근데 이게 너무 많아지면 안되므로 알려주는거 할때 적당히 5분마다 새로고침 된거로 할건데
# 그냥 기존의 watching streamer daemon을 5분마다 call 해주면 사람들이 볼때도 시간 절약 될 뿐만 아니라 view를 5분마다 call 해주는 역할


class RefreshWatchingStreamers(Thread):
    def run(self, *args, **kwargs):
        while True:
            now_streamers = [i[0] for i in popular_streams]
            for streamer in now_streamers:
                result = watching_streamers_daemon(
                    streamer, 300 + random.random() * 100, 600, 100000
                )
                if result:
                    time.sleep(3)


@app.on_event("startup")
@repeat_every(seconds=1000)
def get_new_header() -> None:
    T.header_update()


# @app.on_event("startup")
#   background.background_add()
@app.on_event("startup")
@repeat_every(seconds=1800)
def refresh_search_database() -> None:
    search_data[:] = D.streamers_search_data_update()


@app.on_event("startup")
@repeat_every(seconds=100)
def rank_refresh() -> None:
    D.streamers_data_rank_refresh()


@app.on_event("startup")
@repeat_every(seconds=3600)
def update_bot_list() -> None:
    T.update_bots_list()
    bots_list[:] = D.bots_list()



@app.on_event("startup")
@repeat_every(seconds=200)
def temp_clear_daemon() -> None:
    T.temp_view_clear()
    for i in temp_data:  # temp data 로 인한 메모리 증가세 막기
        time_elapsed = tools.now() - temp_data[i]["time"]
        if time_elapsed.seconds > 200:
            del temp_data[i]


@app.get("/settings", response_class=HTMLResponse)
def settings_refresh():
    settings.init()
    return f"{settings.update_after}, {settings.popular_count}, {settings.viewer_minimum} 새로고침 완료"


menus = {
    "stream": ["/twitch/stream", "현재 켜진 방송 및 스트리머들 목록"],
    "watching": ["/twitch/streamer_watching_streamer", "방송 보는 스트리머"],
    "watch": ["/twitch/watching_broadcasts", "스트리머가 보는 방송"],
    "followed": ["/twitch/followed", "스트리머를 팔로우하는 스트리머"],
    "following": ["/twitch/following", "스트리머가 팔로우하는 스트리머"],
    "as_manager": ["/twitch/as_manager", "매니저로 활동하는 방송"],
    "managers": ["/twitch/managers", "매니저 목록"],
    "rank": ["/twitch/rank", "한국 트위치 팔로워 랭킹"],
    "banned": ["/twitch/banned", "정지 / 탈퇴한 스트리머들 목록"],
    "history": ["/twitch/history", "과거 아이디 / 이름 / 설명 등등"],
    "contact": ["/contact", "버그 제보 / 기능 제안 / Q&A"],
}


@app.get("/twitch/menu", response_class=HTMLResponse)
def menu_provider(remove: Union[str, None] = Query(default=[], max_length=50)):
    result = ""
    for menu, content in menus.items():
        if menu not in remove:
            result += menu_template.render(link=content[0], menu_name=content[1])
    return result


# @app.on_event("startup")
# def init_background() -> None:
#     background.init()
#     RefreshWatchingStreamers(daemon=True).start()

