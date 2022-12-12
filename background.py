from dd import D, T, Streamer
from threading import Thread, Event
from pymongo import MongoClient
import time
from collections import deque
from queue import Queue
import tools
from datetime import timedelta as td
from typing import List, Set, Dict, Tuple, Any
from collections import Counter
client = MongoClient()
db = client.api
once_num = 100
# background tasks는 D,T를 필요로 하는데, D,T에서 threading 등 백그라운드가 필요해버리면 분리가 불가능하다.
# 그런데 애초에, D,T는 실시간 모듈이 아니라 단순 라이브러리 이므로 threading을 사용하는것이 적합하지 않고, 따라서 이러한 문제가 발생한 것이다.
follownum_queue = Queue()
real_follownum_queue = Queue()
id_queue = Queue()
login_queue = Queue()
following_queue = Queue()
lang_to_update = 'ko'
update_after = td(days=1)


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


class GetFromIds(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if id_queue.qsize() and real_follownum_queue.qsize() < 500:
                to_get = []
                while id_queue.qsize() and len(to_get) < 100:
                    to_get.append(id_queue.get())
                updated_result = D.update_from_id(to_get, False)['data']
                for i in updated_result:
                    real_follownum_queue.put(i)
            else:
                time.sleep(1)


class GetFromLogins(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if login_queue.qsize() and real_follownum_queue.qsize() < 500:
                to_get = []
                while login_queue.qsize() and len(to_get) < 100:
                    to_get.append(login_queue.get())
                updated_result = D.update_from_login(to_get, False)['data']
                for i in updated_result:
                    real_follownum_queue.put(i)
            else:
                time.sleep(1)


class CheckFollowersNumFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if follownum_queue.qsize():
                streamer = follownum_queue.get()
                if 'followers' not in streamer or streamer.last_updated<tools.now()-update_after:
                    real_follownum_queue.put(streamer)
            else:
                time.sleep(1)
    # def update_streamers_regularly(self, *args, **kwargs):
    #     while True:


class GetFollowersNumFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if real_follownum_queue.qsize():
                streamer = real_follownum_queue.get()
                streamer.update_followers_num()
                print(f'{streamer.name} follow get')
                time.sleep(0.2)
            else:
                time.sleep(1)


class GetFollowingsFromStreamer(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if following_queue.qsize():
                streamer = following_queue.get()
                print(f'{streamer.name} following get')
                follow_datas_processed = D.follow_data_to_streamers(streamer.follow_from(False,False),'from')
                following_streamers = follow_datas_processed['datas']
                failed_ids = follow_datas_processed['failed_ids']
                for i in failed_ids:
                    id_queue.put(i)
                    # 한번 fail한건 다시 안하기?
                for i in following_streamers:
                    follownum_queue.put(i['streamer'])
            else:
                time.sleep(1)
class GetFollowersNumBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if id_queue.qsize() < 500:
                to_get = list(
                    D.db.streamers_data.find({'followers': {'$exists': False}}, {'_id': 0, 'id': 1}).limit(once_num))
                if to_get:
                    for i in to_get:
                        id_queue.put(i['id'])
                    print('data with no followers added for update')
                else:
                    time.sleep(100)
            else:
                time.sleep(1)


class UpdateBackground(StoppableThread):
    def run(self, *args, **kwargs):
        while not self.stopped():
            if id_queue.qsize() < 500:
                to_update = list(D.db.streamers_data.find(
                    {'lang': lang_to_update, 'banned': False, 'last_updated': {'$lte': tools.now() - update_after}},
                    {'_id': 0, 'id': 1}).sort('localrank', 1).limit(once_num))
                if to_update:
                    for i in to_update:
                        id_queue.put(i['id'])
                    print('old data added for update')
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


background_threads: Dict[str, List[StoppableThread]] = {'from_ids': [GetFromIds(daemon=True)],
                                                        'from_logins': [GetFromLogins(daemon=True)],
                                                        'check_followers': [CheckFollowersNumFromStreamer(daemon=True)],
                                                        'get_followers': [GetFollowersNumFromStreamer(daemon=True)],
                                                        'get_followings':[GetFollowingsFromStreamer(daemon=True)],
                                                        'get_followers_background': [],
                                                        'update_background': []}


def thread_status():
    result = ""
    for i in background_threads:
        status = [j.is_alive() for j in background_threads[i]]
        status_dict = dict(Counter(status))
        result += f"{i} = {', '.join([f'''{['dead', 'alive'][k]}:{v}''' for k, v in status_dict.items()])}<br>"
    return result


def init():
    for i in background_threads:
        for j in background_threads[i]:
            j.start()


# default_threads=[GetFromIds(),GetFromLogins(),CheckFollowersNumFromStreamer(),GetFollowersNumFromStreamer()]


# thread.is_alive
# 정지되면 다시 시작하는 기능 설정
# 각 스레드별 개수 정해서 추가 제거 관리 가능하게
# GetFollowersNumFromStreamer().start()  #double? lol


def background_add():
    background_threads['get_followers_background'].append(GetFollowersNumBackground(daemon=True))
    background_threads['update_background'].append(UpdateBackground(daemon=True))
