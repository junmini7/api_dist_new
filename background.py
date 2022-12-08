from dd import D, T, Streamer
from threading import Thread,Event
from pymongo import MongoClient
import time
from collections import deque
from queue import Queue
import tools
from datetime import timedelta as td


client = MongoClient()
db = client.api
once_num = 100
# background tasks는 D,T를 필요로 하는데, D,T에서 threading 등 백그라운드가 필요해버리면 분리가 불가능하다.
# 그런데 애초에, D,T는 실시간 모듈이 아니라 단순 라이브러리 이므로 threading을 사용하는것이 적합하지 않고, 따라서 이러한 문제가 발생한 것이다.
follownum_queue = Queue()
real_follownum_queue = Queue()
id_queue = Queue()
login_queue=Queue()
lang_to_update = 'ko'
update_after = td(days=1)



class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
class GetFromIds(Thread):
    def run(self, *args, **kwargs):
        while True:
            if id_queue.qsize() and real_follownum_queue.qsize() < 500:
                to_get = []
                while id_queue.qsize() and len(to_get) < 100:
                    to_get.append(id_queue.get())
                updated_result = D.update_from_id(to_get, False)['data']
                for i in updated_result:
                    real_follownum_queue.put(i)
            else:
                time.sleep(1)

class GetFromLogins(Thread):
    def run(self, *args, **kwargs):
        while True:
            if login_queue.qsize() and real_follownum_queue.qsize() < 500:
                to_get = []
                while login_queue.qsize() and len(to_get) < 100:
                    to_get.append(login_queue.get())
                updated_result = D.update_from_login(to_get, False)['data']
                for i in updated_result:
                    real_follownum_queue.put(i)
            else:
                time.sleep(1)
class CheckFollowersNumFromStreamer(Thread):
    def run(self, *args, **kwargs):
        while True:
            if follownum_queue.qsize():
                streamer = follownum_queue.get()
                if 'followers' not in streamer:
                    real_follownum_queue.put(streamer)
            else:
                time.sleep(1)
    # def update_streamers_regularly(self, *args, **kwargs):
    #     while True:


class GetFollowersNumFromStreamer(Thread):
    def run(self, *args, **kwargs):
        while True:
            if real_follownum_queue.qsize():
                streamer = real_follownum_queue.get()
                streamer.update_followers_num()
                print(f'{streamer.name} follow get')
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


class GetFollowingsBackground(Thread):
    def run(self, *args, **kwargs):
        raise NotImplementedError


def init(background=False):
    GetFromIds().start()
    GetFromLogins().start()
    CheckFollowersNumFromStreamer().start()
    GetFollowersNumFromStreamer().start()
    GetFollowersNumFromStreamer().start()  #double? lol
    if background:
        GetFollowersNumBackground().start()
        UpdateBackground().start()
