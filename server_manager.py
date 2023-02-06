import database_manager
import traceback
from fastapi import FastAPI, Query, Request
from fastapi_utils.tasks import repeat_every
from typing import List, Optional, Tuple
from fastapi.middleware.cors import CORSMiddleware
import fastapi.responses
from collections import Counter
import settings
import psutil
import background_manager
import etc_manager


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_data = database_manager.DatabaseHandler.streamers_search_data_update()

global_variable_dicts = {
    "search data": search_data,
    "temp data for gui ": background_manager.watching_streamers_data,
    "temp working for gui": background_manager.watching_streamers_working_dict,
    "bot list": background_manager.bots_list,
    "headers": database_manager.RequestHandler.header,
    "now working on view": database_manager.RequestHandler.now_working_on_view,
    "temp view": database_manager.RequestHandler.temp_view,
    "popular streams": background_manager.popular_streams,
}


# about_new_hakko = f"%s에 해당하는 스트리머는 {follower_requirements}명 미만의 팔로워를 보유하고 있기 때문에 데이터 베이스 상에 추가는 되었지만, 앞으로의 통계에 활용되지는 않습니다. {follower_requirements}명의 이상의 팔로워를 가지게 된다면 다시 시도해주세요."
# about_still_hakko = f"%s에 해당하는 스트리머는 여전히 {follower_requirements}명 미만의 팔로워를 보유하고 있음이 확인되었습니다. {follower_requirements}명의 이상의 팔로워를 가지게 된다면 다시 시도해주세요."
# about_hakko_to_streamers = f"%s에 해당하는 스트리머는 최근 {follower_requirements}명 이상의 팔로워 기록을 갱신하였기 때문에 기존의 보관용 데이터베이스에서 통계용 데이터베이스로 이동되었습니다. 축하드립니다."
# about_streamer_to_hakko = f"%s에 해당하는 스트리머는 최근 {follower_requirements}명 미만의 팔로워로 떨어졌기 때문에 기존의 통계용 데이터베이스에서 보관용 데이터베이스로 이동되었습니다."


@app.middleware("http")
async def logging(request: Request, call_next):
    whattolog = f'{etc_manager.now().strftime("%Y/%m/%d %H:%M:%S")} {str(request.client.host)} {request.method} {request.url.path} {request.path_params} {request.query_params}\n'
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
        return fastapi.responses.HTMLResponse(
            content="서버에 에러가 발생했습니다...", status_code=200
        )


@app.get("/favicon.ico")
async def favicon():
    return fastapi.responses.FileResponse(
        "./favicon.ico", media_type="application/octet-stream", filename="favicon.ico"
    )


def streamers_search_recommend_client(query):
    result = database_manager.DatabaseHandler.streamers_data_name_search(
        query, search_data
    )
    temp = f"<meta charset='utf-8'>'{query}'에 해당하는 스트리머가 없습니다. 스트리머의 이름 또는 아이디 둘 다로 검색 가능하니 다시 한번 해보세요. "
    if len(result) == 1:
        temp += f"<br><a href='/twitch/streamer_watching_streamer/?query={result[0]}'>{result[0]}</a>가 찾고 계신 스트리머 인가요? 만약 그렇다면 링크를 누르세요."
    elif len(result) > 1:
        temp += f"<br>혹시 {', '.join([f'''<a href='/twitch/streamer_watching_streamer/?query={rec}'>{rec}</a>''' for rec in result])} 중에 찾고 계신 스트리머가 있나요? "
    return temp


def query_parser(query) -> Tuple[str, database_manager.Streamer]:
    broadcaster = database_manager.DatabaseHandler.streamers_search(query)
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


@app.get("/twitch/populariswatchingapi/", response_class=fastapi.responses.HTMLResponse)
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
    background_manager.watching_streamers_daemon(broadcaster)
    return background_manager.watching_streamers_maker(
        broadcaster, follower_requirements
    )


# f"<div class='row col-12 col-md-11 centering centering_text gx-5'>{} {}</div><br>"


@app.get("/twitch/watchingbroadcasts", response_class=fastapi.responses.HTMLResponse)
def watching_broadcasts(
    request: Request,
    query: str,
    tolerance: Optional[int] = settings.tolerance_for_watching_broadcasts,
):
    ip = str(request.client.host)
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    # following_data = {i['to_id']: i for i in broadcaster.follow_from()}
    # followed_data = {i['from_id']: i for i in broadcaster.follow_to()}
    known_logins = []
    watching_logins = []
    total_viewers = 0
    for login in list(database_manager.RequestHandler.temp_view):
        if (
            etc_manager.now() - database_manager.RequestHandler.temp_view[login]["time"]
        ).seconds <= tolerance:
            known_logins.append(login)
            total_viewers += len(
                database_manager.RequestHandler.temp_view[login]["view"]["viewers"]
            )
            if (
                broadcaster.login
                in database_manager.RequestHandler.temp_view[login]["view"]["viewers"]
            ):
                watching_logins.append(login)
    if known_logins:
        result = f"총 {total_viewers}명이 보고 있는 {len(known_logins)}개의 방송 중 {broadcaster.introduce}가 보고 있는 방송은 "
        if watching_logins:
            result += f'다음과 같습니다. <br><div class="row" style="margin-left:4px; margin-right:2px;">{"".join([database_manager.DatabaseHandler.streamers_search(i).introduce_html for i in watching_logins])}</div>'
        else:
            result += "없습니다."
    else:
        result = "시청목록이 아예 없습니다 죄송합니당"
    buttons = broadcaster.buttons(["watching_broadcasts"])
    return (
        result
        + f"""<div class='row col-12 col-md-11 centering centering_text gx-5'>{''.join(buttons)}</div>"""
    )


@app.get(
    "/twitch/populariswatchingapi/{query}",
    response_class=fastapi.responses.HTMLResponse,
)
def please_reload(response_class=fastapi.responses.HTMLResponse):
    return "please reload"


@app.get("/twitch/populariswatching/")
async def popular_is_watching_introduce(request: Request):
    return fastapi.responses.RedirectResponse(
        "https://woowakgood.live/twitch/streamer_watching_streamer/"
    )


@app.get("/twitch/populariswatching/{query}")
async def popular_is_watching(request: Request, query: str):
    return fastapi.responses.RedirectResponse(
        f"https://woowakgood.live/twitch/streamer_watching_streamer?query={query}"
    )


@app.get("/loading.gif")
async def loadinggif():
    return fastapi.responses.RedirectResponse(
        "https://woowakgood.live/loading-2.gif"
    )  # FileResponse('loading.gif', media_type='application/octet-stream', filename='loading.gif')


@app.get("/twitch/managers/{query}", response_class=fastapi.responses.HTMLResponse)
async def managers(request: Request, query: str, refresh: Optional[bool] = False):
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    managers_data_processed = database_manager.DatabaseHandler.role_data_to_streamers(
        broadcaster.role_broadcaster(False, refresh), "broadcaster"
    )
    manager_streamers = managers_data_processed["datas"]
    total_manager = managers_data_processed["total"]
    background_manager.processed_putter(managers_data_processed)
    # managers_data=broadcaster.role_broadcaster(False)
    # managers_infos = {i['id']: Streamer(i) for i in D.db.streamers_data.find(
    #     {'id': {'$in': [i[f"member_id"] for i in managers_data]}})}
    role_infos = dict(Counter([i["role"] for i in manager_streamers if i["valid"]]))
    role_infos_gui = ", ".join(
        [f"{etc_manager.role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
    )
    return (
        f'<meta charset="utf-8">{broadcaster.introduce} 방송에서 활동하는 매니저 혹은 VIP, 스태프들은 총 {total_manager}명 이며, 각각 {role_infos_gui}입니다. <br>'
        + "<br>".join(
            [
                f"""<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {inf['streamer'].followers}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {broadcaster.name}의 방송에서 {etc_manager.role_to_ko[inf['role']]} {f'을 했었고 현재는 해고당함' if not inf['valid'] else ''}"""
                for inf in manager_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/as_manager/{query}", response_class=fastapi.responses.HTMLResponse)
async def as_manager(request: Request, query: str, refresh: Optional[bool] = True):
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    managers_data_processed = database_manager.DatabaseHandler.role_data_to_streamers(
        broadcaster.role_member(False), "member"
    )
    manager_streamers = managers_data_processed["datas"]
    total_manager = managers_data_processed["total"]
    role_infos = dict(Counter([i["role"] for i in manager_streamers if i["valid"]]))
    role_infos_gui = ", ".join(
        [f"{etc_manager.role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
    )

    return (
        f'<meta charset="utf-8">{broadcaster.introduce}가 매니저 혹은 VIP, 스태프로 활동하는 방송들은 총 {total_manager}개 이며, 각각 {role_infos_gui}입니다. <br>'
        + "<br>".join(
            [
                f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {etc_manager.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {etc_manager.yi(broadcaster.name)} 이 방송에서 {etc_manager.role_to_ko[inf['role']]} {'을 했었고 현재는 해고당함' if not inf['valid'] else ''}"
                # , {inf['last_updated']}에 마지막으로 확인
                for inf in manager_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/following/{query}", response_class=fastapi.responses.HTMLResponse)
def following_by_popular(
    request: Request,
    query: str,
    by: Optional[str] = "time",
    reverse: Optional[bool] = False,
    refresh: Optional[bool] = False,
    valid: Optional[bool] = True,
):
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    # 기존에 팔로우에서 나온 id를 모듈 측에서 업데이트 하려고 했지만 그걸 굳이 비실시간 모듈에서 하기 보다는 실시간 모듈에서 호출할때 해주는게 맞다.
    follow_datas_processed = database_manager.DatabaseHandler.follow_data_to_streamers(
        broadcaster.follow_from(refresh, valid), "from", by, reverse
    )
    following_streamers = follow_datas_processed["datas"]
    total_follow = follow_datas_processed["total"]
    background_manager.processed_putter(follow_datas_processed)
    # Thread(target=D.get_follower_from_streamers, args=(to_streamers, False)).start()
    return (
        f'<meta charset="utf-8">{broadcaster.introduce}가 팔로우하는 스트리머들은 총 {total_follow}명입니다. ({etc_manager.order_dict[by][reverse]} 순)<br>'
        + (
            f"여기 안보이는 {total_follow - len(following_streamers)}명의 스트리머는 정지당하거나, 현재 업데이트 중이기 때문에 볼 수 없습니다.<br>"
            if total_follow - len(following_streamers) != 0
            else ""
        )
        + "<br>".join(
            [
                f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {etc_manager.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {etc_manager.yi(broadcaster.name)} {inf['when']}에 팔로우, {inf['last_updated']}에 마지막으로 확인"
                if inf["valid"]
                else f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {etc_manager.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {etc_manager.yi(broadcaster.name)} {inf['when']}에 팔로우, 및 {inf['last_updated']}에 팔로우 취소한 것 확인 (확인한 시점)"
                for inf in following_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get(
    "/twitch/followedbypopular/{query}", response_class=fastapi.responses.HTMLResponse
)
def followed_by_popular(
    request: Request,
    query: str,
    by: Optional[str] = "canceled",
    reverse: Optional[bool] = False,
    follower_requirements: Optional[int] = 3000,
    valid: Optional[bool] = True,
):
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    followed_streamers_processed = (
        database_manager.DatabaseHandler.follow_data_to_streamers(
            broadcaster.follow_to(valid),
            "to",
            by,
            reverse,
            max(follower_requirements, 10),
        )
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
        f'<meta charset="utf-8">{broadcaster.introduce}를 팔로우하는 {follower_requirements}명 이상의 팔로워를 가진 스트리머는 {total_follow}명입니다. ({etc_manager.order_dict[by][reverse]} 순)<br>'
        + "<br>".join(
            [
                f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {etc_manager.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {etc_manager.eul(broadcaster.name)} {inf['when']}에 팔로우, {inf['last_updated']}에 마지막으로 확인"
                if inf["valid"]
                else f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={inf['streamer'].login}'><img src='{inf['streamer'].profile_image}' width='100' height='100'></a> {inf['streamer'].name} ({inf['streamer'].login}), 팔로워 {etc_manager.numtoko(inf['streamer'].followers)}명, {inf['streamer'].country} {inf['streamer'].localrank}위, {etc_manager.eul(broadcaster.name)} {inf['when']}에 팔로우, 및 {inf['last_updated']}에 팔로우 취소한 것 확인 (확인한 시점)"
                for inf in following_streamers
            ]
        )
        + """<br><div class='text-center'><button class='btn btn-primary' id='copy_link' onclick='copyToClipboard(window.location.href)'>현재 보고 있는 결과 링크 복사하기</button></div><br>"""
    )


@app.get("/twitch/relationship/", response_class=fastapi.responses.HTMLResponse)
async def relationship(logins: List[str] = Query(None)):
    raise NotImplementedError


@app.get("/twitch/ranking/", response_class=fastapi.responses.HTMLResponse)
def ranking(request: Request, lang: Optional[str] = "ko", num: Optional[int] = 5000):
    ranking_datas = list(
        database_manager.DatabaseHandler.streamers_data_ranking(num, lang)
    )
    return (
        f'<meta charset="utf-8">{etc_manager.langcode_to_country(lang)} 내 팔로워 랭킹<br>'
        + f'트위치에서 정지당한 스트리머는 본 목록에 뜨지 않으므로 다음을 참조하세요. <a href="/twitch/banned">정지당한 스트리머 목록</a><br>'
        + "<br>".join(
            [
                f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={v['login']}'><img src='{v['profile_image_url']}' width='100' height='100'></a> {v['display_name']} ({v['login']}), 팔로워 {v['followers']}명, {etc_manager.langcode_to_country(v['lang'])} {v['localrank']}위 (last update on {v['last_updated']})"
                for v in ranking_datas
            ]
        )
    )


@app.get("/twitch/banned/", response_class=fastapi.responses.HTMLResponse)
def banned_ui(request: Request, lang: Optional[str] = "ko"):
    banned_list = list(database_manager.DatabaseHandler.currently_banned(lang))
    return (
        f'<meta charset="utf-8">현재 트위치에서 정지당한 스트리머들 목록<br>'
        + "<br>".join(
            [
                f"<a href='{etc_manager.home_url}/twitch/streamer_watching_streamer/?query={v['login']}'><img src='{v['profile_image_url']}' width='100' height='100'></a> {v['display_name']} ({v['login']}) ({etc_manager.passed_time(v['banned_history'][-1])}전에 마지막으로 밴먹은것 확인) {'팔로워 %d명, %s, %s전에 마지막으로 확인' % (v['followers'], str(v['localrank']), etc_manager.passed_time(v['last_updated'])) if 'followers' in v and 'localrank' in v else ''}"
                for v in banned_list
            ]
        )
        + f"<br><a href='{etc_manager.api_url}/twitch/addlogin/?{'&'.join(['logins=' + k['login'] for k in banned_list])}&skip_already_done=false&give_chance_to_banned=true'>여기 등장하는 {len(banned_list)}명의 정지당한 스트리머들 새로고침하기"
    )


@app.get("/twitch/fired", response_class=fastapi.responses.HTMLResponse)
def fired_ui(request: Request, lang: Optional[str] = "ko"):
    fired_list = list(database_manager.DatabaseHandler.role_fired())
    ids_set = {i["broadcaster_id"] for i in fired_list} | {
        i["member_id"] for i in fired_list
    }
    id_to_data = {
        i["id"]: database_manager.Streamer(i)
        for i in database_manager.DatabaseHandler.db.streamers_data.find(
            {
                "id": {"$in": list(ids_set)},
                "lang": lang,
                "followers": {"$gte": 10},
            }
        )
    }
    result_first = ""
    result_second = ""
    for fired in fired_list:
        if fired["broadcaster_id"] in id_to_data and fired["member_id"] in id_to_data:
            result_first += f"{id_to_data[fired['member_id']]}는 {id_to_data[fired['broadcaster_id']]}의 {etc_manager.role_to_ko[fired['role']]}이었으나 해고됨 ({fired['last_updated']}에 확인)<br>"
        else:
            result_second += f"{fired['member_id']}는 {fired['broadcaster_id']}의 {etc_manager.role_to_ko[fired['role']]}이었으나 해고됨 ({fired['last_updated']}에 확인)<br>"

    return result_first + result_second


@app.get("/twitch/unfollow", response_class=fastapi.responses.HTMLResponse)
def unfollow_ui(request: Request, lang: Optional[str] = "ko"):
    unfollow_list = list(database_manager.DatabaseHandler.unfollow())
    ids_set = {i["from_id"] for i in unfollow_list} | {
        i["to_id"] for i in unfollow_list
    }
    id_to_data = {
        i["id"]: database_manager.Streamer(i)
        for i in database_manager.DatabaseHandler.db.streamers_data.find(
            {
                "id": {"$in": list(ids_set)},
                "lang": lang,
                "followers": {"$gte": 10},
            }
        )
    }
    result_first = ""
    result_second = ""
    for unfollow in unfollow_list:
        if unfollow["from_id"] in id_to_data and unfollow["to_id"] in id_to_data:
            result_first += f"{id_to_data[unfollow['from_id']]}는 {id_to_data[unfollow['to_id']]}를 {unfollow['when']}에 팔로우 했으나 현재 언팔로우함 ({unfollow['last_updated']}에 마지막 확인)<br>"
        else:
            result_second += f"{unfollow['from_id']}는 {unfollow['to_id']}를 {unfollow['when']}에 팔로우 했으나 현재 언팔로우함 ({unfollow['last_updated']}에 마지막 확인)<br>"

    return result_first + result_second


# @app.get("/twitch/viewerintersection")
# async def viewerintersection(request: Request, streamers: List[str] = Query(None)):
#     ip = str(request.client.host)
#     intersect = D.viewer_intersection(streamers)
#     with open('log.txt', 'a') as f:
#         f.write(
#             f'{dt.now().strftime("%Y/%m/%d %H:%M:%S")} viewerintersection {" ".join(streamers)} from {ip} {" ".join(map(str, intersect))}\n')
#     return intersect


@app.get("/twitch/streams", response_class=fastapi.responses.HTMLResponse)
async def streams(request: Request, number: Optional[int] = 4):
    result = ""
    for j, i in enumerate(background_manager.popular_streams):
        streamer = i[0]
        stream = i[1]
        thumb_url = (
            stream["thumbnail_url"]
            .replace("{width}", "1280")
            .replace("{height}", "720")
        )
        viewer_count = etc_manager.numtoko(stream["viewer_count"])
        follower = etc_manager.numtoko(streamer.followers)
        # uptime = tools.tdtoko(stream['uptime'])
        stream_country = "한국"
        stream_rank = j + 1
        if streamer.id in background_manager.watching_streamers_data:
            # crawled_time = str(temp_data[streamer.id]['time'])
            viewer_data = "".join(
                [
                    i["rendered"]
                    for i in background_manager.watching_streamers_data[streamer.id][
                        "datas"
                    ][:number]
                ]
            )
            result += etc_manager.stream_info_template.render(
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
            result += etc_manager.stream_info_template.render(
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
    peop = database_manager.RequestHandler.view(streamer)
    result = list(set(peop) & set(ids))
    with open("log.txt", "a") as f:
        f.write(
            f'{etc_manager.now().strftime("%Y/%m/%d %H:%M:%S")} multiple {" ".join(ids)} iswatching {streamer} from {ip} {" ".join(map(str, result))}\n'
        )

    return result


def streamers_data_update_to_ko(result, follow_result):
    explanation = "<meta charset='utf-8'> 데이터베이스 추가/업데이트 작업이 완료되었습니다."
    for i in etc_manager.description:
        if result[i]:
            explanation += "<br>" + etc_manager.description[i] % (
                ", ".join([str(j) for j in result[i]])
            )
    for i in etc_manager.follow_description:
        if follow_result[i]:
            explanation += "<br>" + etc_manager.follow_description[i] % (
                ", ".join([str(j) for j in follow_result[i]])
            )
    return explanation


@app.get("/twitch/addlogin/", response_class=fastapi.responses.HTMLResponse)
def add_logins(
    request: Request,
    logins: List[str] = Query(None),
    skip: Optional[bool] = False,
    update_follow: Optional[bool] = True,
    follower_requirements: Optional[int] = 3000,
):
    if not etc_manager.is_valid_logins(logins):
        return "make sure if the ID is made up of only alphabets, numbers and under bar"
    background_manager.login_queue.extend(logins)
    update_result = database_manager.DatabaseHandler.update_from_login(logins, skip)
    follow_update_result = database_manager.DatabaseHandler.get_follower_from_streamers(
        update_result["data"], update_follow
    )
    return streamers_data_update_to_ko(update_result, follow_update_result)


@app.get("/twitch/history/{query}", response_class=fastapi.responses.HTMLResponse)
def past_logins(request: Request, query: str):
    parse_result = query_parser(query)
    if parse_result[0] != "active":
        return parse_result[1]
    broadcaster = parse_result[1]
    result = {}
    for i in ["banned_history", "past_login", "past_display_name", "past_description"]:
        if i in broadcaster:
            result[i] = broadcaster[i]
    if not result:
        return f"{broadcaster.introduce}는 과거 기록이 없습니다."
    return f"{broadcaster.introduce}의 {', '.join([f'{etc_manager.eun(etc_manager.history_to_ko[k])} {v}' for k, v in result.items()])}<br>(11월 전에는 아이디만 바뀌어도 정지되었다고 판단하는 바람에 그 당시의 정지기록은 의미가 없습니다.)"


@app.get("/twitch/stats", response_class=fastapi.responses.HTMLResponse)
def statistics():
    return (
        f"전체 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({})}<br>"
        f"팔로워 수 정보가 있는 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({'followers': {'$exists': True}})}<br>"
        f"팔로잉 수 정보가 있는 스트리머 수 {database_manager.DatabaseHandler.db.follow_data_information.count_documents({})}<br>"
        f"팔로워 관계 수 {database_manager.DatabaseHandler.db.follow_data.count_documents({})}<br>"
        f"한국 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({'lang': 'ko'})}<br>"
        f"로컬 랭크가 있는 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({'localrank': {'$exists': True}})}<br>"
        f"글로벌 랭크가 있는 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({'globalrank': {'$exists': True}})}<br>"
        f"밴 당한 스트리머 수 {database_manager.DatabaseHandler.db.streamers_data.count_documents({'banned': True})}<br>"
        f"매니저 정보가 있는 스트리머 수 {database_manager.DatabaseHandler.db.role_data_information.count_documents({})}<br>"
        f"매니저 관계 수 {database_manager.DatabaseHandler.db.role_data.count_documents({})}<br>"
    )


# @app.get("/threadnum", response_class=HTMLResponse)
# def thread_num():
#     return threading.active_count()


@app.get("/twitch/status", response_class=fastapi.responses.HTMLResponse)
def status():
    return "<br>".join(
        [
            background_manager.thread_status(),
            background_manager.queue_status(),
            temp_status(),
            settings_status(),
            temp_variable_status(),
        ]
    )

    #      memory_status(),


def settings_status():
    return "<br>".join([f"{k}:{v}" for k, v in settings.data.items()])


def memory_status():
    return "<br>".join(
        [f"{i}:{etc_manager.obj_size_str(j)}" for i, j in global_variable_dicts.items()]
    )


def temp_variable_status():
    result = {
        "watching_streamers_working_dict_status": "".join(
            [
                f"{value['broadcaster']} {value['status']} {etc_manager.passed_time(value['time'])}<br>"
                for value in background_manager.watching_streamers_working_dict.values()
                if value['status'] != "idle"
            ]
        ),
        "watching_streamers_data_status": "".join(
            [
                f"{value['broadcaster']} {etc_manager.passed_time(value['time'])}<br>"
                for value in background_manager.watching_streamers_data.values()
            ]
        ),
        "temp_view_status": "".join(
            [
                f"{login} {len(data['view']['viewers'])} {etc_manager.passed_time(data['time'])}<br>"
                for login, data in database_manager.RequestHandler.temp_view.items()
            ]
        ),
        "now_working_on_view_status": "".join(
            [
                f"{login} {value}<br>"
                for login, value in database_manager.RequestHandler.now_working_on_view.items()
            ]
        ),
    }
    return "".join(
        [
            f"{status_type}<br>{status_content}<br><br>"
            for status_type, status_content in result.items()
        ]
    )


def temp_status():
    try:
        return "<br>".join(
            [
                f'{k}{"".join([f"<br>&emsp;{i.current} {i.high} {i.critical}" for i in v])}'
                for k, v in psutil.sensors_temperatures().items()
            ]
        )
    except:
        return ""


@app.get("/settings", response_class=fastapi.responses.HTMLResponse)
def settings_refresh():
    settings.init()
    return f"{settings.data} 새로고침 완료"


@app.get("/twitch/thread_manage", response_class=fastapi.responses.RedirectResponse)
def thread_manager(name: str, num: int):
    background_manager.thread_num_manager(name, num)
    return "/twitch/status"


# 헷갈린 이유가, 이거의 목적이 첫번째는 100명 크롤링해서 보는 사람 알려주는거고 두번째는 쫙 목록 보여주는거
# 근데 이게 너무 많아지면 안되므로 알려주는거 할때 적당히 5분마다 새로고침 된거로 할건데
# 그냥 기존의 watching streamer daemon을 5분마다 call 해주면 사람들이 볼때도 시간 절약 될 뿐만 아니라 view를 5분마다 call 해주는 역할


@app.on_event("startup")
@repeat_every(seconds=1000)
def get_new_header() -> None:
    database_manager.RequestHandler.header_update()


# @app.on_event("startup")
#   background_manager.background_add()
@app.on_event("startup")
@repeat_every(seconds=1800)
def refresh_search_database() -> None:
    search_data[:] = database_manager.DatabaseHandler.streamers_search_data_update()


@app.on_event("startup")
@repeat_every(seconds=100)
def rank_refresh() -> None:
    database_manager.DatabaseHandler.streamers_data_rank_refresh()


@app.on_event("startup")
@repeat_every(seconds=3600)
def update_bot_list() -> None:
    database_manager.RequestHandler.update_bots_list()
    background_manager.bots_list[:] = database_manager.DatabaseHandler.bots_list()


@app.on_event("startup")
@repeat_every(seconds=200)
def temp_clear_daemon() -> None:
    database_manager.RequestHandler.temp_view_clear()
    for i in background_manager.watching_streamers_data:  # temp data 로 인한 메모리 증가세 막기
        time_elapsed = (
            etc_manager.now() - background_manager.watching_streamers_data[i]["time"]
        )
        if time_elapsed.seconds > 200:
            del background_manager.watching_streamers_data[i]


@app.on_event("startup")
def init_background() -> None:
    background_manager.init()
