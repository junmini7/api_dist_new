import database_manager
from threading import Thread, Event
from pymongo import MongoClient
import time
from collections import deque, Counter, defaultdict
import datetime
from typing import List, Set, Dict, Tuple, Any, Deque
from collections import Counter
import settings
import etc_manager
import random

client = MongoClient()
db = client.api
once_num = 100
# background tasks는 D,T를 필요로 하는데, D,T에서 threading 등 백그라운드가 필요해버리면 분리가 불가능하다.
# 그런데 애초에, D,T는 실시간 모듈이 아니라 단순 라이브러리 이므로 threading을 사용하는것이 적합하지 않고, 따라서 이러한 문제가 발생한 것이다.


follownum_queue: Deque[database_manager.Streamer] = deque()
id_queue: Deque[str] = deque()
login_queue: Deque[str] = deque()
following_queue: Deque[database_manager.Streamer] = deque()
role_queue: Deque[database_manager.Streamer] = deque()
update_queue: Deque[database_manager.Streamer] = deque()
watching_queue: Deque[database_manager.Streamer] = deque()
lang_to_update = "ko"
popular_streams = []

queues_dict = {
    "watching": watching_queue,
    "follownum": follownum_queue,
    "id": id_queue,
    "login": login_queue,
    "following": following_queue,
    "update": update_queue,
    "role": role_queue,
}


class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = Event()
        self.last_updated = etc_manager.now()
        self.daemon = True

    def __str__(self):
        return self.__class__.__name__

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class GetFromStreamers(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if update_queue:
                streamer = update_queue.popleft()
                self.name = str(streamer)
                assert isinstance(streamer, database_manager.Streamer)
                if (
                        "followers" not in streamer
                        or streamer.last_updated < etc_manager.now() - settings.update_after
                ):
                    id_queue.append(streamer.id)
            else:
                self.name = "idle"
                time.sleep(1)


class GetFromIds(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if id_queue and len(follownum_queue) < 500:
                self.name = str(len(follownum_queue))
                to_get = []
                while id_queue and len(to_get) < 100:
                    to_get.append(id_queue.popleft())
                updated_result = database_manager.DatabaseHandler.update_from_id(
                    to_get, False
                )["data"]
                follownum_queue.extend(updated_result)
            else:
                self.name = "idle"
                time.sleep(1)


class GetFromLogins(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if login_queue and len(follownum_queue) < 500:
                self.name = str(len(login_queue))
                to_get = []
                while login_queue and len(to_get) < 100:
                    to_get.append(login_queue.popleft())
                updated_result = database_manager.DatabaseHandler.update_from_login(
                    to_get, False
                )["data"]
                follownum_queue.extend(updated_result)
            else:
                self.name = "idle"
                time.sleep(1)


# class CheckFollowersNumFromStreamer(StoppableThread):
#     def run(self, *args, **kwargs):
#         while not self.stopped():
#             if follownum_queue.qsize():
#                 streamer = follownum_queue.get()
#                 if 'followers' not in streamer or streamer.last_updated<tools.now()-update_after:
#                     follownum_queue.put(streamer)
#             else:
#                 time.sleep(1)
#     # def update_streamers_regularly(self, *args, **kwargs):
#     #     while True:


class GetFollowersNumFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if follownum_queue:
                to_update_streamer = follownum_queue.popleft()
                self.name = str(to_update_streamer)
                to_update_streamer.refresh_followers_num()  # update_followers_num ??
            else:
                self.name = "idle"
                time.sleep(1)


class GetFollowingsFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if following_queue:
                streamer = following_queue.popleft()
                self.name = str(streamer)
                # print(f'{streamer.name} following get')
                follow_datas_processed = (
                    database_manager.DatabaseHandler.follow_data_to_streamers(
                        streamer.follow_from(False, False), "from"
                    )
                )
                following_streamers = follow_datas_processed["datas"]
                failed_ids = follow_datas_processed["failed_ids"]
                for i in failed_ids:
                    id_queue.append(i)
                    # 한번 fail한건 다시 안하기?
                for i in following_streamers:
                    follownum_queue.append(i["streamer"])
                time.sleep(5)
            else:
                self.name = "idle"
                time.sleep(1)


class GetRoleFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if role_queue:
                streamer = role_queue.popleft()
                self.name = str(streamer)
                managers_data_processed = (
                    database_manager.DatabaseHandler.role_data_to_streamers(
                        streamer.role_broadcaster(False, False), "broadcaster"
                    )
                )
                # follow_datas_processed = (
                #     database_manager.DatabaseHandler.follow_data_to_streamers(
                #         streamer.follow_from(False, False), "from"
                #     )
                # )
                processed_putter(managers_data_processed)
                # processed_putter(follow_datas_processed)
                time.sleep(5)
            else:
                self.name = "idle"
                time.sleep(1)


class GetFollowersNumBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if len(id_queue) < 500:
                self.name = str(len(id_queue))
                to_get = list(
                    database_manager.DatabaseHandler.db.streamers_data.find(
                        {"followers": {"$exists": False}}, {"_id": 0, "id": 1}
                    ).limit(once_num)
                )
                if to_get:
                    for i in to_get:
                        id_queue.append(i["id"])
                    # print('data with no followers added for update')
                else:
                    time.sleep(100)
            else:
                self.name = "idle"
                time.sleep(1)


class UpdateBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if len(id_queue) < 500:
                self.name = str(len(id_queue))
                to_update = list(
                    database_manager.DatabaseHandler.db.streamers_data.find(
                        {
                            "lang": lang_to_update,
                            "banned": False,
                            "last_updated": {
                                "$lte": etc_manager.now() - settings.update_after
                            },
                        },
                        {"_id": 0, "id": 1},
                    )
                    .sort("localrank", 1)
                    .limit(once_num)
                )
                if to_update:
                    for i in to_update:
                        id_queue.append(i["id"])
                    # print('old data added for update')
                else:
                    time.sleep(100)
            else:
                self.name = "idle"
                time.sleep(1)


class UpdateBannedBackground(StoppableThread):
    def run(self, *args, **kwargs):
        raise NotImplementedError


class GetFollowingsBackground(StoppableThread):
    def run(self, *args, **kwargs):
        raise NotImplementedError


class UpdatePopularStreams(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            res = database_manager.DatabaseHandler.stream_data_to_streamers(
                database_manager.RequestHandler.streams_info(
                    settings.popular_count, "ko"
                )
            )
            datas = res["datas"]
            failed = res["failed_ids"]
            id_queue.extend(failed)
            popular_streams[:] = [
                i for i in datas if i[1]["viewer_count"] > settings.viewer_minimum
            ]
            self.name = str(len(popular_streams))
            time.sleep(60)


class RefreshWatchingStreamers(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            now_streamers = [i[0] for i in popular_streams]
            for streamer in now_streamers:
                self.name = str(streamer)
                if streamer.id in watching_streamers_data:
                    time_elapsed = (
                            etc_manager.now() - watching_streamers_data[streamer.id]["time"]
                    )
                    if (
                            time_elapsed.seconds
                            > settings.streams_allow_maximum + random.random() * 100
                    ):
                        watching_streamers_worker(streamer)
                else:
                    watching_streamers_worker(streamer)

                # watching_streamers_daemon(
                #     streamer,
                #     settings.streams_allow_maximum + random.random() * 100,
                #     refresh=False,
                #     wait=False,
                # )
                time.sleep(0.5)


class GetWatchingStreamersFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            self.last_updated = etc_manager.now()
            if watching_queue:
                streamer = watching_queue.popleft()
                self.name = str(streamer)
                assert isinstance(streamer, database_manager.Streamer)
                if streamer.id in watching_streamers_data:
                    time_elapsed = (
                            etc_manager.now() - watching_streamers_data[streamer.id]["time"]
                    )
                    if time_elapsed.seconds > settings.refresh_maximum_default:
                        watching_streamers_worker(streamer)
                else:
                    watching_streamers_worker(streamer)
            else:
                self.name = "idle"
                time.sleep(0.2)


background_thread_default_num: Dict[str, int] = {
    "watching_streamers": 4,
    "update_streams": 1,
    "refresh_streams": 1,
    "from_streamers": 1,
    "from_ids": 1,
    "from_logins": 1,
    "get_followers": 1,
    "get_followings": 1,
    "get_roles": 1,
    "get_followers_background": 0,
    "update_background": 0,
}
background_thread = {
    "watching_streamers": GetWatchingStreamersFromStreamer,
    "update_streams": UpdatePopularStreams,
    "refresh_streams": RefreshWatchingStreamers,
    "from_streamers": GetFromStreamers,
    "from_ids": GetFromIds,
    "from_logins": GetFromLogins,
    "get_followers": GetFollowersNumFromStreamer,
    "get_followings": GetFollowingsFromStreamer,
    "get_roles": GetRoleFromStreamer,
    "get_followers_background": GetFollowersNumBackground,
    "update_background": UpdateBackground,
}
background_thread_instances: Dict[str, List[StoppableThread]] = {
    thread_type: [background_thread[thread_type](daemon=True) for i in range(num)]
    for thread_type, num in background_thread_default_num.items()
}


#     {
#     "watching_streamers":[GetWatchingStreamersFromStreamer(daemon=True),GetWatchingStreamersFromStreamer(daemon=True),GetWatchingStreamersFromStreamer(daemon=True),GetWatchingStreamersFromStreamer(daemon=True)],
#     "refresh_streams":[RefreshWatchingStreamers(daemon=True)],
#     "from_streamers": [GetFromStreamers(daemon=True)],
#     "from_ids": [GetFromIds(daemon=True)],
#     "from_logins": [GetFromLogins(daemon=True)],
#     "get_followers": [GetFollowersNumFromStreamer(daemon=True)],
#     "get_followings": [GetFollowingsFromStreamer(daemon=True)],
#     "get_roles": [GetRoleFromStreamer(daemon=True)],
#     "get_followers_background": [],
#     "update_background": [],
# }


def processed_putter(processed):
    id_queue.extend(processed["failed_ids"])
    update_queue.extend([i["streamer"] for i in processed["datas"]])


def thread_status():
    # result_dict=defaultdict(list)
    # for thread_type,threads in background_thread_instances.items():
    #     for thread in threads:
    #         result_dict[thread.is_alive()].append([thread_type,thread.name])
    #
    #     # status = [j.is_alive() for j in background_thread_instances[i]]
    #     # status_dict = dict(Counter(status))
    #     # result += f"{i} = {', '.join([f'''{['dead', 'alive'][k]}:{v}''' for k, v in status_dict.items()])}<br>"
    # result='<br>'.join([f"{['Dead','Alive'][is_alive]}<br>{''.join([f'&emsp;{thread[0]} : {thread[1]}<br>' for thread in threads])}" for is_alive,threads in result_dict.items()])
    return "<br>".join(
        [
            f"""{thread_type} {' '.join([f'<a href="/twitch/thread_manage?name={thread_type}&num={num}">{num}</a>' for num in range(5)])}<br>&emsp;{",".join([f"<span style='color:{['red', 'black'][thread.is_alive()]}'>{thread.name} {etc_manager.passed_time(thread.last_updated) if not thread.is_alive() else ''}</span>" for thread in threads])}"""
            for thread_type, threads in background_thread_instances.items()
        ]
    )


def queue_status():
    return "<br>".join([f"{i}:{len(j)}" for i, j in queues_dict.items()])


def thread_num_manager(thread_name, num):
    for i in background_thread_instances:
        for j in background_thread_instances[i]:
            if not j.is_alive():
                background_thread_instances[i].remove(j)
    while len(background_thread_instances[thread_name]) > num:
        to_delete = background_thread_instances[thread_name].pop()
        to_delete.stop()
        print("removed")
    while len(background_thread_instances[thread_name]) < num:
        new_thread = background_thread[thread_name](daemon=True)
        background_thread_instances[thread_name].append(new_thread)
        new_thread.start()
        print("added")


def init():
    for i in background_thread_instances:
        for j in background_thread_instances[i]:
            j.start()


# default_threads=[GetFromIds(),GetFromLogins(),CheckFollowersNumFromStreamer(),GetFollowersNumFromStreamer()]


# thread.is_alive
# 정지되면 다시 시작하는 기능 설정
# 각 스레드별 개수 정해서 추가 제거 관리 가능하게
# GetFollowersNumFromStreamer().start()  #double? lol


def background_add():
    background_thread_instances["get_followers_background"].append(
        GetFollowersNumBackground(daemon=True)
    )
    background_thread_instances["update_background"].append(
        UpdateBackground(daemon=True)
    )


watching_streamers_data = {}
watching_streamers_working_dict = {}
bots_list = database_manager.DatabaseHandler.bots_list()


def watching_streamers_daemon(broadcaster: database_manager.Streamer):
    if broadcaster.id in watching_streamers_data:  # 이전에 한게 있을 때
        time_elapsed = (
                etc_manager.now() - watching_streamers_data[broadcaster.id]["time"]
        )
        if time_elapsed.seconds < settings.allow_maximum_default:  # 이전에 한게 충분히 좋을때
            if time_elapsed.seconds > settings.refresh_maximum_default:
                watching_queue.append(
                    broadcaster
                )  # 이 더해주는 프로세스는 worker 외부에 이뤄져야 하므로 daemon필요
                # print(f'reserved work for {broadcaster}')
            # else:
            # print(f'already working on {broadcaster}')
            # print(f'using result of {broadcaster} on {temp_data[broadcaster.id]["time"]}')
            return False

    if (
            broadcaster.id in watching_streamers_working_dict
            and watching_streamers_working_dict[broadcaster.id]['status']
            == "working"  # 이전에 한게 너무 오래되거나, 없어서 일하는 중이면 기다렸다가 하면 됨
    ):
        while True:
            if watching_streamers_working_dict[broadcaster.id]['status'] == "idle":
                return True
            elif watching_streamers_working_dict[broadcaster.id]['status'] == "error":
                watching_streamers_worker(broadcaster)
                return True
            time.sleep(1)
    watching_streamers_worker(broadcaster)  # 없거나 오래됬는데 안하고 있으면 직접 하기
    return True


def watching_streamers_worker(broadcaster: database_manager.Streamer):
    if (
            broadcaster.id not in watching_streamers_working_dict
            or watching_streamers_working_dict[broadcaster.id]['status'] != "working"  # 실행중이지 않을때
    ):
        now = etc_manager.now()
        watching_streamers_working_dict[broadcaster.id] = {'status': "working", "time": etc_manager.now(),
                                                           'broadcaster': broadcaster}
        # broadcaster.refresh_followers_num()
        try:
            update_queue.append(broadcaster)
            watchers = broadcaster.watching_streamers(50)
            start_time = time.time()
            update_queue.extend(watchers["viewers"])
            viewers_id = [i.id for i in watchers["viewers"]]
            following_data = {i["to_id"]: i for i in broadcaster.follow_from()}
            assert broadcaster.followers >= 0
            assert broadcaster.localrank
            followed_data = {i["from_id"]: i for i in broadcaster.follow_to()}
            role_data = {
                i["member_id"]: i for i in broadcaster.role_broadcaster(True, False)
            }
            role_crawled_watchers_ids = [
                j["id"]
                for j in database_manager.DatabaseHandler.db.role_data_information.find(
                    {"id": {"$in": viewers_id}}
                )
            ]
            follow_crawled_watchers_ids = [
                j["id"]
                for j in database_manager.DatabaseHandler.db.follow_data_information.find(
                    {"id": {"$in": viewers_id}}
                )
            ]
            for streamer in watchers["viewers"]:
                if streamer.followers > 1000:
                    if streamer.id not in follow_crawled_watchers_ids:
                        following_queue.append(streamer)
                    if streamer.id not in role_crawled_watchers_ids:
                        role_queue.append(streamer)
            head = ""
            if watchers["broadcaster"]:
                head += f'{broadcaster.name}({broadcaster.login}) 현재 Broadcaster 접속중 <a href="https://twitch.tv/{broadcaster.login}"><img src="https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/3" width="15" height="15"/></a><br>'
            head += f"{broadcaster.introduce}{etc_manager.onlyeul(broadcaster.name)} 지금 시청 중인 {watchers['count']}명의 로그인 시청자 중 팔로워 수 %d명 이상의 스트리머"
            buttons = broadcaster.buttons(["streamer_watching_streamer"])
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
            watching_streamers_data[broadcaster.id] = {
                "broadcaster": broadcaster,
                "time": now,
                "head": head,
                "datas": streamer_temp_data,
                "buttons": buttons,
            }
            print(
                f"watching_streamers_worker took {time.time() - start_time}s for {broadcaster.name}"
            )
            watching_streamers_working_dict[broadcaster.id] = {'status': "idle", "time": etc_manager.now(),
                                                           'broadcaster': broadcaster}
        except:
            watching_streamers_working_dict[broadcaster.id] = {'status': "error", "time": etc_manager.now(),
                                                           'broadcaster': broadcaster}


def watching_streamers_maker(
        broadcaster: database_manager.Streamer, follower_requirements: int
):
    start_time = time.time()
    assert broadcaster.id in watching_streamers_data

    data = watching_streamers_data[broadcaster.id]
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
        [f"{etc_manager.role_to_ko[k]}가 {v}명" for k, v in role_infos.items()]
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
            etc_manager.button_templete(
                f"{etc_manager.api_url}/twitch/addlogin/?logins={broadcaster.login}&{'&'.join(['logins=' + k['login'] for k in streamer_temp_data])}&skip_already_done=false&give_chance_to_hakko=true",
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
        <p><i class='fa-solid fa-heart red'></i> : {etc_manager.gwa(broadcaster.name)} 해당 스트리머가 상호 팔로우</p>
        <p><i class='fa-solid fa-heart'></i> : 해당 스트리머만 {etc_manager.eul(broadcaster.name)} 팔로우</p>
        <p><i class='fa-solid fa-heart green'></i> : {broadcaster.name}만 해당 스트리머를 팔로우</p>
        <p><i class='fa-regular fa-heart'></i> : 서로 팔로우 하지 않음</p>
        <p><i class='fa-solid fa-question'></i> : 팔로우 목록을 아직 조사하지 않음</p>
        <p> 날짜는 각 스트리머가 {etc_manager.eul(broadcaster.name)} 팔로우한 일시입니다.</p>
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


def streamer_info_maker(
        streamer: database_manager.Streamer,
        broadcaster: database_manager.Streamer,
        now: datetime.datetime,
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
        role_icon = (
            f'<img src="{etc_manager.role_to_icon[role]}" width="15" height="15"/>'
        )
    else:
        role = ""
        role_icon = ""
    followers = streamer.followers
    rendered = etc_manager.streamer_info_template.render(
        login=streamer.login,
        image_url=streamer.profile_image,
        name=streamer.name,
        follower=etc_manager.numtoko(followers),
        country=streamer.country,
        rank=streamer.localrank,
        time=etc_manager.passed_time(streamer.last_updated),
        icon=mutual_info[1],
        following=mutual_info[2],
        api_url=etc_manager.api_url,
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


def mutual_follow_information(
        following_data: dict,
        followed_data: dict,
        broadcaster: database_manager.Streamer,
        streamer: database_manager.Streamer,
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
