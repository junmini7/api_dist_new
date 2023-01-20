from core import D, T, Streamer
from threading import Thread, Event
from pymongo import MongoClient
import time
from collections import deque
import tools
from datetime import timedelta as td
from typing import List, Set, Dict, Tuple, Any, Deque
from collections import Counter
import settings

client = MongoClient()
db = client.api
once_num = 100
# background tasks는 D,T를 필요로 하는데, D,T에서 threading 등 백그라운드가 필요해버리면 분리가 불가능하다.
# 그런데 애초에, D,T는 실시간 모듈이 아니라 단순 라이브러리 이므로 threading을 사용하는것이 적합하지 않고, 따라서 이러한 문제가 발생한 것이다.

follownum_queue: Deque[Streamer] = deque()
id_queue: Deque[str] = deque()
login_queue: Deque[str] = deque()
following_queue: Deque[Streamer] = deque()
role_queue: Deque[Streamer] = deque()
update_queue: Deque[Streamer] = deque()
lang_to_update = "ko"


class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = Event()

    def __str__(self):
        return self.__class__.__name__

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class GetFromStreamers(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if update_queue:
                streamer = update_queue.popleft()
                assert isinstance(streamer, Streamer)
                if (
                    "followers" not in streamer
                    or streamer.last_updated < tools.now() - settings.update_after
                ):
                    id_queue.append(streamer.id)
            else:
                time.sleep(1)


class GetFromIds(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if id_queue and len(follownum_queue) < 500:
                to_get = []
                while id_queue and len(to_get) < 100:
                    to_get.append(id_queue.popleft())
                updated_result = D.update_from_id(to_get, False)["data"]
                follownum_queue.extend(updated_result)
            else:
                time.sleep(1)


class GetFromLogins(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if login_queue and len(follownum_queue) < 500:
                to_get = []
                while login_queue and len(to_get) < 100:
                    to_get.append(login_queue.popleft())
                updated_result = D.update_from_login(to_get, False)["data"]
                follownum_queue.extend(updated_result)
            else:
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
            if follownum_queue:
                follownum_queue.popleft().refresh_followers_num()  # update_followers_num ??
            else:
                time.sleep(1)


class GetFollowingsFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if following_queue:
                streamer = following_queue.popleft()
                # print(f'{streamer.name} following get')
                follow_datas_processed = D.follow_data_to_streamers(
                    streamer.follow_from(False, False), "from"
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
                time.sleep(1)


class GetRoleFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if role_queue:
                streamer = role_queue.popleft()
                managers_data_processed = D.role_data_to_streamers(
                    streamer.role_broadcaster(False, False), "broadcaster"
                )
                follow_datas_processed = D.follow_data_to_streamers(
                    streamer.follow_from(False, False), "from"
                )
                processed_putter(follow_datas_processed)
                time.sleep(5)
            else:
                time.sleep(1)


class GetFollowersNumBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if len(id_queue) < 500:
                to_get = list(
                    D.db.streamers_data.find(
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
                time.sleep(1)


class UpdateBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if len(id_queue) < 500:
                to_update = list(
                    D.db.streamers_data.find(
                        {
                            "lang": lang_to_update,
                            "banned": False,
                            "last_updated": {"$lte": tools.now() - settings.update_after},
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
                time.sleep(1)


class UpdateBannedBackground(StoppableThread):
    def run(self, *args, **kwargs):
        raise NotImplementedError


class GetFollowingsBackground(StoppableThread):
    def run(self, *args, **kwargs):
        raise NotImplementedError


background_thread_instances: Dict[str, List[StoppableThread]] = {
    "from_streamers": [GetFromStreamers(daemon=True)],
    "from_ids": [GetFromIds(daemon=True)],
    "from_logins": [GetFromLogins(daemon=True)],
    "get_followers": [GetFollowersNumFromStreamer(daemon=True)],
    "get_followings": [GetFollowingsFromStreamer(daemon=True)],
    "get_roles": [GetRoleFromStreamer(daemon=True)],
    "get_followers_background": [],
    "update_background": [],
}

background_thread = {
    "from_streamers": GetFromStreamers,
    "from_ids": GetFromIds,
    "from_logins": GetFromLogins,
    "get_followers": GetFollowersNumFromStreamer,
    "get_followings": GetFollowingsFromStreamer,
    "get_roles": GetRoleFromStreamer,
    "get_followers_background": GetFollowersNumBackground,
    "update_background": UpdateBackground,
}


def processed_putter(processed):
    id_queue.extend(processed["failed_ids"])
    update_queue.extend([i["streamer"] for i in processed["datas"]])


def thread_status():
    result = ""
    for i in background_thread_instances:
        status = [j.is_alive() for j in background_thread_instances[i]]
        status_dict = dict(Counter(status))
        result += f"{i} = {', '.join([f'''{['dead', 'alive'][k]}:{v}''' for k, v in status_dict.items()])}<br>"
    return result


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
