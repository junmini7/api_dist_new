from __future__ import annotations
from pymongo import MongoClient, DeleteOne, ReplaceOne, UpdateOne, UpdateMany, InsertOne
import tools
import requests
import json
from typing import List, Set, Dict, Tuple, Any
import time
import difflib
from datetime import timedelta as td
update_after = td(days=1)

headers = {
    'Accept': '*/*',
    'Accept-Language': 'ko-KR',
    'Authorization': 'OAuth k1m0skugp28vljvc3o6sza9wceiwo2',
    'Client-Id': 'kimne78kx3ncx6brgo4mv6wki5h1ko',
    'Client-Integrity': 'v4.public.eyJjbGllbnRfaWQiOiJraW1uZTc4a3gzbmN4NmJyZ280bXY2d2tpNWgxa28iLCJjbGllbnRfaXAiOiIxNC4zNi4xNC4yOCIsImRldmljZV9pZCI6InJtSWRHdWZFdFdLdEQxUldtdGhrZTdFeHNQeXFnNXhEIiwiZXhwIjoiMjAyMi0xMi0xMlQwMzo1Mzo0MloiLCJpYXQiOiIyMDIyLTEyLTExVDExOjUzOjQyWiIsImlzX2JhZF9ib3QiOiJmYWxzZSIsImlzcyI6IlR3aXRjaCBDbGllbnQgSW50ZWdyaXR5IiwibmJmIjoiMjAyMi0xMi0xMVQxMTo1Mzo0MloiLCJ1c2VyX2lkIjoiNTY2NzAxMzI5In0sNeAW-h1NigpB3lOjfNYHk_6g1DncXRoDRHMtaqrWRPq3wRZuZOhrXZOOgoJhzE4vAJBSuFgUlKtS0ujwmqML',
    'Client-Session-Id': '17f57ee266d86bdb',
    'Client-Version': 'da7047c5-0f4f-4d43-98a8-0b23fa12e223',
    'Connection': 'keep-alive',
    'Content-Type': 'text/plain;charset=UTF-8',
    'Origin': 'https://www.twitch.tv',
    'Referer': 'https://www.twitch.tv/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
    'X-Device-Id': 'rmIdGufEtWKtD1RWmthke7ExsPyqg5xD',
    'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}
# https://dev.twitch.tv/docs/api/reference
"""In [20]: col.find_one()
Out[20]: {'_id': 1, 'value': {'key1': '200'}}

In [21]: col.update({'_id': 1}, {'$set': {'value.key2': 300}})
Out[21]: {'n': 1, 'nModified': 1, 'ok': 1, 'updatedExisting': True}

In [22]: col.find_one()
Out[22]: {'_id': 1, 'value': {'key1': '200', 'key2': 300}}
EDIT

If your key is in variable all you need is concatenation:

In [37]: key2 = 'new_key'

In [38]: col.update({'_id': 1}, {'$set': {'value.' + key2: 'blah'}})
Out[38]: {'n': 1, 'nModified': 1, 'ok': 1, 'updatedExisting': True}

In [39]: col.find_one()
Out[39]: {'_id': 1, 'value': {'key1': '200', 'new_key': 'blah'}}
"""
"""Korean
ko
search
searchjl
unihan
"""

api_url = 'https://woowakgood.live:8007'
roles = ['vips', 'moderators']  # , 'staff', 'admins', 'global_mods']

"""1. python ValueError
2. python IndexError
3. python SyntaxError
4. python NameError
5. python ZeroDivisionError
6. python FileNotFoundError
7. python TypeError
8. python AttributeError
9. python KeyError 
10. python OverFlowError"""


# to do
# ???????????? ???????????? ????????????
# role id ?????? ?????????
# ???????????? ??? ????????? ??????????????? ?????? data??? ?????????

# D ???????????? ??????????????? ???????????? Streamer ?????? id??? ?????? (????????? ?????? ???????????? ????????? ?????? ?????? ??????)
# ?????? streamers_info_api_from_streamer ?????? ban ?????? ????????? ??????????????? List[Streamer] ???

class Streamer:
    def __init__(self, data):
        assert isinstance(data, dict)
        assert all(field in data for field in ['_id', 'id', 'login', 'display_name'])
        # _id??? assert???????????? ????????? streamer db?????? ???????????? find ?????? ?????? ?????? Streamer ????????? ????????? ?????? ???
        self.data = data
        #
        # else:
        #     temp_data = dm.streamers_data_search(query, followers_requirements)
        #     if temp_data:
        #         self.data = temp_data
        #     else:
        #         raise ValueError

    def __gt__(self, other):
        if isinstance(other, int):
            return self.followers > other
        elif isinstance(other, Streamer):
            return self.followers > other.followers
        else:
            raise TypeError

    def __str__(self):
        return f"{self.name}({self.login})"

    def __repr__(self):
        return f"{self.name}({self.login},{self.id})"

    @property
    def introduce(self):
        return f"{self.country} ??? ????????? ????????? <a href='{api_url}/twitch/addlogin/?logins={self.login}&skip_already_done=false&give_chance_to_hakko=true'>{self.localrank}???({self.followers}???, {tools.tdtoko(tools.now() - self.last_updated)}??? ??????)</a> ??? {self.name} ({self.login})"

    def __eq__(self, other):
        if not isinstance(other, Streamer):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self.id == other.id

    def __getitem__(self, item):
        return self.data[item]

    def __contains__(self, item):
        return item in self.data

    @property
    def abbreviate(self):
        return f"{self.id},{self.login}"

    def refresh(self):
        self.data = D.db.streamers_data.find_one({'_id': self._id})

    def update_with_datas(self, update_data):
        # ???????????? _id??? ????????? ????????????, ?????????
        try:
            D.db.streamers_data.update_one({'_id': self._id}, update_data)
        except:
            print(update_data)
        self.refresh()

    """
    self refresh ??????
    >>> a=dd.D.streamers_data_ranking_login(num=300)
    >>> b=dd.D.streamers_data_update_from_login(a)
    got info of 300 streamers from api in 3.461009979248047s
    rank refreshing took 0.38994932174682617s
    updated 300 datas in 0.6125853061676025s
    
    ?????????
    >>> a=dd.D.streamers_data_ranking_login(num=300)
    >>> b=dd.D.streamers_data_update_from_login(a)
    got info of 300 streamers from api in 3.454845905303955s
    rank refreshing took 0.41212987899780273s
    updated 300 datas in 0.6920623779296875s
    
    ???????
    ??????????
    
    ?????? _id??? ?????? ???????????? ???????????? ?????? ?????? ?????? ?????????????
    
    """

    def update_itself(self):
        result = D.update_from_id([self.id], True)
        self.refresh()
        return result

    def update(self, data):
        if 'display_name' in data:
            data['clear_display_name'] = tools.clear_name(data['display_name'])
        data['banned'] = False
        update_data = {'$set': data, '$push': {}}
        # If the field is absent in the document to update, $push adds the array field with the value as its element.
        assert 'id' not in data or data['id'] == self.id
        if 'login' in data and data['login'] != self.login:
            update_data['$push']['past_login'] = self.login
        if 'display_name' in data and data['display_name'] != self.name:
            update_data['$push']['past_display_name'] = self.name
        if 'description' in data and data['description'] != self.description:
            update_data['$push']['past_description'] = self.description
        self.update_with_datas(update_data)
        return self

    def watching_streamers(self, follower_requirements: int = -1):  # -> Dict[str, List[Streamer]]:
        start_time = time.time()
        watchers = T.view(self.login)
        # managers = self.role_update(watchers) ????????? irc ????????? ??????
        every_watchers = T.role_adder(watchers) + watchers['viewers']
        result = {'broadcaster': watchers['broadcaster'], 'count': watchers['count']}
        if follower_requirements == -1:
            # db.collection.find( { $query: {}, $orderby: { age : -1 } } )
            result['viewers'] = [Streamer(i) for i in
                                 D.db.streamers_data.find({'login': {'$in': every_watchers}}).sort("followers", -1)]
        else:
            result['viewers'] = [Streamer(i) for i in D.db.streamers_data.find(
                {'login': {'$in': every_watchers}, 'followers': {'$gte': max(follower_requirements, 100)}}).sort(
                "followers",
                -1)]

        #     popular_watching_list = [k for k in allthewatchers if
        #                              k in streamers_data and 'ranking' in streamers_data[k] and streamers_data[k][
        #                                  'followers'] > 30]
        # ?????? ?????? ????????? for?????? ?????? ?????? ?????? ??????
        # cls.db.streamers_data.find({'login': {'$in': viewers}})
        with open('log_new.txt', 'a') as f:
            f.write(
                f'{tools.now().strftime("%Y/%m/%d %H:%M:%S")} {self.abbreviate} {result["count"]} polulariswatching {" ".join([i.abbreviate for i in result["viewers"]])}\n')

        print(f'watching streamer for {repr(self)} took {time.time() - start_time}s')
        return result

    # https://stackoverflow.com/questions/72099862/mongo-java-set-values-and-push-to-array-with-previous-values-in-one-command
    # db.collection.update({},
    # [{
    # $set: {
    #   timestamp: 12345,
    #   mean_ninety_percentile: 0.111,
    #   history: {
    #     $cond: [
    #       // <Array condition goes here>
    #       {
    #         $eq: [
    #           "$timestamp",
    #           12345
    #         ]
    #       },
    #       // True part (timestamp not changed: keep history)
    #       "$history",
    #       // False part (timestamp changed: add state to history)
    #       {
    #         $concatArrays: [
    #           {
    #             $ifNull: [
    #               "$history",
    #               []
    #             ]
    #           },
    #           [
    #             // add current state to history
    #             {
    #               timestamp: "$timestamp",
    #               mean_ninety_percentile: "$mean_ninety_percentile"
    #             }
    #           ]
    #       }
    #     ]
    #   }
    # }
    # }],
    # {
    #   upsert: true
    # })

    def ban(self):
        self.update_with_datas({'$set': {'banned': True}, '$push': {'banned_history': tools.now()}})

    def update_roles(self):
        print(f'updating roles of {self.login}')
        start_time = time.time()
        datas = T.role_from_broadcaster(self.login)
        print(f'getting role api took {time.time() - start_time}s')
        D.role_update_all(datas, self)

    def update_followers_num(self):
        self.update_with_datas({'$set': {'followers': T.followed(self.id, 100)['total'], 'last_updated': tools.now()}})

    def update_followings(self, end=-1):
        print(f'updating following of {self.login}')
        start_time = time.time()
        req = T.following(self.id, end)
        print(f'getting following api took {time.time() - start_time}s')
        if req['ended']:
            D.follow_update_all(req['data'], self)
        else:
            D.follow_update_partial(req['data'], self)

    # ??????????????? ????????? ?????? ??????????????? role update??? ????????? ??????
    # $in?????? ??? ??????(???????????????)
    # Streamer ????????? ?????? ????????????
    def follow_crawled(self):
        data=D.db.follow_data_information.find_one({'id': self.id})
        if not data:
            return False
        if tools.now()-data['last_updated']>update_after:
            return False
        return data


    def follow_from(self, refresh: bool = False, valid_necessary: bool = True):
        if not self.follow_crawled() or refresh:
            self.update_followings()
        return D.follow(self.id, 'from', valid_necessary)
        # assert not valid_necessary or D.db.follow_data_information.find_one({'id': self.id})['following_num'] == len(result)
        # follow reqments ?????? assert ?????? X

    def is_following(self, to_streamer: Streamer, update_following=True, valid_necessary=True):
        if not self.follow_crawled():
            if update_following:
                self.update_followings()
            else:
                raise FileNotFoundError
        return D.follow_check(self.id, to_streamer.id, valid_necessary)

    def follow_to(self, valid_necessary=True):
        return D.follow(self.id, 'to', valid_necessary)

    def role_crawled(self):
        return D.db.role_data_information.find_one({'id': self.id})

    def role_broadcaster(self, valid_necessary=True, refresh: bool = False):
        if not self.role_crawled() or refresh:
            try:
                self.update_roles()
            except:
                open('twitchapierror.txt', 'a').write(f"{self}, {tools.now()}\n")
        return D.role(self.id, 'broadcaster', valid_necessary)

    def role_member(self, valid_necessary=True):
        return D.role(self.id, 'member', valid_necessary)

    """
    By default :meth:find_one_and_update returns the original version of the document before the update was applied. To return the updated version of the document instead, use the return_document option.

You can limit the fields returned with the projection option.

The upsert option can be used to create the document if it doesn't already exist.

If multiple documents match filter, a sort can be applied."""

    # ?????? ???????????? ?????? ??????????????? -1 ??????????????? ????????? ?????????, ?????? ???????????? ????????? ?????????????????? ??????????????? ????????? ???
    @property
    def last_updated(self):
        try:
            return self.data['last_updated']
        except:
            # self.update_followers_num()
            return -1  # self.data['last_updated']

    @property
    def _id(self):
        return self.data['_id']

    @property
    def login(self):
        return self.data['login']

    @property
    def id(self):
        return self.data['id']

    @property
    def name(self):
        return self.data['display_name']

    @property
    def followers(self):
        try:
            return self.data['followers']
        except:
            # self.update_followers_num()
            return -1  # self.data['followers']

    @property
    def lang(self):
        return self.data['lang']

    @property
    def country(self):
        return tools.langcode_to_country(self.lang)

    @property
    def localrank(self):
        try:
            return self.data['localrank']
        except:
            # self.update_followers_num()
            return -1

    @property
    def globalrank(self):
        try:
            return self.data['globalrank']
        except:
            # self.update_followers_num()
            return -1

    @property
    def created_at(self):
        return self.data['created_at']

    @property
    def profile_image(self):
        return self.data['profile_image_url']

    @property
    def view_count(self):
        return self.data['view_count']

    @property
    def description(self):
        return self.data['description']

    @property
    def banned(self):
        return self.data['banned']

    @property
    def banned_history(self):
        try:
            return self.data['banned_history']
        except:
            return -1


class D:
    client = MongoClient()
    db = client.api

    # ?????????  ?????? D??? ????????????????????? ????????? ?????? ??????????????? ????????? ??????????
    # ?????? ??????????????? static??? property??? ????????? ????????? static?????? property ????????????
    @classmethod
    def api_key(cls):
        return list(cls.db.api_key.find())

    @classmethod
    def logins_data(cls):
        return set(cls.db.logins_data.find_one()['data'])

    # @classmethod
    # def logins_data(self, logins_data):
    #     # if not is_valid_logins(logins_data):
    #     #     raise ValueError("invalid logins data")
    #     self.db.logins_data.update_one({}, {'$set': {'data': list(logins_data)}}, upsert=True)

    @classmethod
    def bots_list(cls, online=True):
        if online:
            return cls.db.bots_list.find_one()['online']
        return cls.db.bots_list.find_one()['all']

    @classmethod
    def login_to_id(cls, login):
        return cls.db.streamers_data.find_one({'login': login})['id']

    @classmethod
    def id_to_login(cls, id):
        return cls.db.streamers_data.find_one({'id': id})['login']

    @classmethod
    def streamers_data(cls, search_by, query):
        data_temp = cls.db.streamers_data.find_one({search_by: query})
        if data_temp:
            return Streamer(data_temp)
        else:
            return None

    # if asked id doesn't exist, update from id?

    @classmethod
    def streamers_datas(cls, search_by: str, queries: List[str], need_for_unknown_queries: bool = True):
        # start_time = time.time()
        assert isinstance(queries, list)
        known_streamers = [Streamer(i) for i in cls.db.streamers_data.find({search_by: {'$in': queries}})]
        if need_for_unknown_queries:
            unknown_queries = list(set(queries) - {i[search_by] for i in known_streamers})
            # assert len(known_streamers) + len(unknown_queries) == len(queries)
            return known_streamers, unknown_queries
        else:
            # print(f"streamers_datas single took {time.time() - start_time}s")
            return known_streamers

    # @classmethod
    # def streamers_datas(cls, search_by: str, queries: List[str], need_for_unknown_queries: bool = True):
    #     start_time=time.time()
    #     known_streamers, unknown_queries = [], []
    #     for query in queries:
    #         data_temp = cls.streamers_data(search_by, query)
    #         if data_temp:
    #             known_streamers.append(data_temp)
    #         else:
    #             unknown_queries.append(query)
    #     if need_for_unknown_queries:
    #         return known_streamers, unknown_queries
    #     print(f"streamers_datas single took {time.time()-start_time}s")
    #     return known_streamers

    @classmethod
    def streamers_data_name_search(cls, query: str, search_data) -> List[str]:
        return difflib.get_close_matches(query, search_data)

    @classmethod
    def streamers_search_data_update(cls):
        search_data = set.union(
            *[{i['login'], i['display_name'], i['clear_display_name']} for i in cls.streamers_data_raw()])
        cls.db.search_data.update_one({}, {'$set': {'data': list(search_data)}}, upsert=True)
        return list(search_data)

    @classmethod
    def streamers_search_data(cls):
        return cls.db.search_data.find_one({})['data']

    @classmethod
    def streamers_search(cls, query: str, followers_requirements: int = 30) -> Streamer:
        data_temp = cls.db.streamers_data.find_one({"login": query.lower()})
        if data_temp:
            return Streamer(data_temp)
        data_temp = cls.db.streamers_data.find_one(
            {"display_name": query, "followers": {"$gte": followers_requirements}})
        if data_temp:
            return Streamer(data_temp)
        data_temp = cls.db.streamers_data.find(
            {"clear_display_name": tools.clear_name(query), "followers": {"$gte": followers_requirements}}).sort(
            "followers", -1).limit(1)
        try:
            return Streamer(data_temp[0])
        except IndexError:
            pass
        if query.isnumeric():
            data_temp = cls.db.streamers_data.find_one({"id": query})
            if data_temp:
                return Streamer(data_temp)
        if tools.is_valid_login(query):
            data_temp = cls.update_from_login([query])['data']
            if data_temp:
                return data_temp[0]

        # return False, cls.streamers_data_name_search(query)
        # if tools.isvalidlogin(query):

        # return self.db.streamers_data.find({"followers": {"$gte": followers_requirements}, "$text": {"$search": query}},
        #                                    {"score": {"$meta": "textScore"}}).sort("score", {"$meta": "textScore"})
        # db.streamers_data.create_index([("display_name", pymongo.TEXT)])

    @classmethod
    def update_from_login(cls, logins_queue: List[str], skip: bool = True) -> dict:  # return streamers
        # assert isinstance(logins_queue, (set, list))
        logins_queue = list(set([i.lower() for i in logins_queue]))
        logins_queue, invalid_logins = tools.collect_valid_logins(logins_queue)
        known_streamers, unknown_logins = cls.streamers_datas('login', logins_queue)
        # cls.streamers_data_multiple('login', logins_queue)
        if unknown_logins:
            reqs, failed = T.streamers_info_api_from_login(unknown_logins)
        else:
            reqs, failed = [], []
        if not skip:
            reqs_temp, banned_streamers = T.streamers_info_api_from_streamer(known_streamers)
            reqs += reqs_temp
        else:
            banned_streamers = []
        if reqs:
            added, updated = cls.streamers_datas_update(reqs)
        else:
            added, updated = [], []
        return {'added': added, 'updated': updated, 'invalid': invalid_logins, 'failed': failed,
                'banned': banned_streamers, 'skipped': known_streamers if skip else [],
                'data': added + updated + known_streamers if skip else added + updated}

    @classmethod
    def update_from_id(cls, ids_queue: List[str], skip: bool = True) -> dict:  # return streamers
        ids_queue = list(set(ids_queue))
        known_streamers, unknown_ids = cls.streamers_datas('id', ids_queue)
        # cls.streamers_data_multiple('login', logins_queue)
        if unknown_ids:
            reqs, failed = T.streamers_info_api_from_id(unknown_ids)
        else:
            reqs, failed = [], []
        if not skip:
            reqs_temp, banned_streamers = T.streamers_info_api_from_streamer(known_streamers)
            reqs += reqs_temp
        else:
            banned_streamers = []
        if reqs:
            added, updated = cls.streamers_datas_update(reqs)
        else:
            added, updated = [], []
        return {'added': added, 'updated': updated, 'failed': failed,
                'banned': banned_streamers if not skip else [], 'skipped': known_streamers if skip else [],
                'data': added + updated + known_streamers if skip else added + updated}

    @classmethod
    def get_follower_from_streamers(cls, streamers: List[Streamer], update_follow: bool = True) -> dict[
        str, list[Streamer] | list[Any]]:
        assert all(isinstance(i, Streamer) for i in streamers)
        to_update = streamers if update_follow else [streamer for streamer in streamers if 'followers' not in streamer]
        not_update = [] if update_follow else [streamer for streamer in streamers if 'followers' in streamer]
        for streamer in to_update:
            streamer.update_followers_num()
        # if to_update:
        #     cls.streamers_data_rank_refresh()
        return {'follow_updated': to_update, 'follow_skipped': not_update}
        # streamer??? ??????????????? ????????? ???????????? ????????? ???

    @classmethod
    def streamers_data_raw(cls):
        return list(cls.db.streamers_data.find())

    @classmethod
    def streamers_data_insert_one(cls, data):
        assert all(field in data for field in ['id', 'login', 'display_name'])
        data['clear_display_name'] = tools.clear_name(data['display_name'])
        result = cls.db.streamers_data.insert_one(data)
        # cls.streamers_data_rank_refresh()
        return result

    @classmethod
    def streamers_data_insert_many(cls, datas):
        for data in datas:
            assert all(field in data for field in ['id', 'login', 'display_name'])
            data['clear_display_name'] = tools.clear_name(data['display_name'])
        result = cls.db.streamers_data.insert_many(datas)
        # if datas:
        #     cls.streamers_data_rank_refresh()
        return result

    @classmethod
    def streamers_data_with(cls, field, exist=True):
        return cls.db.streamers_data.find({field: {'$exists': exist}})

    @classmethod
    def streamers_datas_update(cls, datas):
        start_time = time.time()
        updated = []
        id_to_data = {i['id']: i for i in datas}
        streamers_to_update = cls.streamers_datas('id', list(id_to_data.keys()), False)
        print(f"found streamers_to_update datas in {time.time() - start_time}s")
        streamers_id = [i.id for i in streamers_to_update]
        to_add = [i for i in datas if i['id'] not in streamers_id]  # ????????? ?????? ?????? ????????? ??? ????????? ?????????
        print(f"found to_add datas in {time.time() - start_time}s")
        if to_add:

            added_ids = cls.streamers_data_insert_many(to_add).inserted_ids if to_add else []
            print(f"added datas in {time.time() - start_time}s")
            added = cls.streamers_datas('_id', added_ids, False)
            print(f"found datas in {time.time() - start_time}s")
        else:
            added = []
        for streamer in streamers_to_update:
            updated.append(streamer.update(id_to_data[streamer.id]))
        # for data in datas:
        #     data_old = cls.streamers_data('id', data['id'])  # find({'id':{'$in':[i['id'] for i in datas]}}) ??????
        #     if data_old:
        #         updated.append(data_old.update(data))
        #         # ????????? update??? ????????? ??? ????????? ?????? ????????? ?????? ??????, ????????? skip ?????? ???
        #     else:
        #         to_add.append(data)

        # if updated or added:
        #     cls.streamers_data_rank_refresh()
        print(f"updated {len(datas)} datas in {time.time() - start_time}s")
        return added, updated

    @classmethod
    def streamers_data_update(cls, data: dict) -> Tuple[str, Streamer]:  # (str, Streamer)
        streamer_id = data['id']
        data_old = cls.streamers_data('id', streamer_id)
        if data_old:
            data_old.update(data)
            return 'updated', data_old
        else:
            inserted_id = cls.streamers_data_insert_one(data).inserted_id
            return 'added', cls.streamers_data('_id', inserted_id)

    # ???????????? ?????? ?????? id ????????? ?????? upsert true ???????????? result?????? upsert ????????? ???????????? ?????????, history ?????? ????????? ????????? ???????????????...
    @classmethod
    def streamers_data_update_general(cls, search_by: str, query: str, data: dict):
        if 'display_name' in data:
            data['clear_display_name'] = tools.clear_name(data['display_name'])
        result = cls.db.streamers_data.update_one({search_by: query}, {'$set': data}, upsert=True)
        # cls.streamers_data_rank_refresh()
        return result

    @classmethod
    def streamers_data_rank_refresh(cls):
        start_time = time.time()
        cls.db.streamers_data.aggregate([
            {"$match":
                 {"banned": False,
                  "followers": {"$exists": True},
                  "lang": {"$exists": True}}
             },
            {'$project': {'followers': 1, 'lang': 1}},
            {
                "$setWindowFields":
                    {
                        "partitionBy": "$lang",
                        "sortBy": {"followers": -1},
                        "output": {
                            "localrank": {
                                "$rank": {}
                            }
                        }
                    }
            },
            {
                "$setWindowFields":
                    {
                        "sortBy": {"followers": -1},
                        "output": {
                            "globalrank": {
                                "$rank": {}
                            }
                        }
                    }
            },
            {'$project': {'localrank': 1, 'globalrank': 1}},
            {
                "$merge": "streamers_data"
            }
        ])
        print(f'rank refreshing took {time.time() - start_time}s')

    @classmethod
    def streamers_data_ranking(cls, num=float('inf'), lang="ko"):
        if lang == 'global':
            # return self.db.streamers_data.aggregate([
            #     {
            #         "$match":
            #             {"globalrank":
            #                  {"$lte": num}
            #              }
            #     },
            #     {
            #         "$sort":
            #             {
            #                 "globalrank": 1
            #             }
            #     }
            # ])  # we cant use this because its cursor
            return cls.db.streamers_data.find({'globalrank': {'$lte': num}}).sort("globalrank", 1)
        else:
            return cls.db.streamers_data.find({'localrank': {'$lte': num}, 'lang': lang}).sort(
                "localrank", 1)

    @classmethod
    def streamers_data_ranking_login(cls, num=float('inf'), lang="ko", ):
        if lang == 'global':
            return [i['login'] for i in
                    cls.db.streamers_data.find({'globalrank': {'$lte': num}}, {'_id': 0, 'login': 1}).sort("globalrank",
                                                                                                           1)]
        else:
            return [i['login'] for i in
                    cls.db.streamers_data.find({'localrank': {'$lte': num}, 'lang': lang}, {'_id': 0, 'login': 1}).sort(
                        "localrank", 1)]

    @classmethod
    def currently_banned(cls):
        return cls.db.streamers_data.find({'banned': True})

    @classmethod
    def small_streamers(cls, follower_requirements):
        return cls.db.streamers_data.find({'followers': {'$lt': follower_requirements}}, {'_id': 0, 'login': 1})

    @classmethod
    def role(cls, id, position, valid_necessary=True):
        if not valid_necessary:
            valid_necessary = {"$exists": True}
        return cls.db.role_data.find({f"{position}_id": id, 'valid': valid_necessary})

    @classmethod
    def role_check(cls, broadcaster_id, member_id, valid_necessary=True):
        return cls.db.role_data.find_one(
            {"broadcaster_id": broadcaster_id, "member_id": member_id, 'valid': valid_necessary})

    # ?????? ????????? ?????? filter ?????????

    # {'id': '67708794', 'login': 'nix', 'name': 'Nix', 'when': datetime.datetime(2022, 10, 23, 19, 5, 27), 'last_updated': datetime.datetime(2022, 10, 23, 20, 37, 11, 574842)}
    # {'from_id': '49045679', 'from_login': 'woowakgood', 'from_name': '?????????', 'to_id': '693895624', 'to_login': 'wakphago', 'to_name': '?????????_', 'followed_at': 10-01T13:11:39Z'},
    # ?????? ?????? ????????? ???????????? ???????????? ?????? ?????? ????????? ???
    @classmethod
    def follow(cls, id, direction, valid_necessary=True):
        if not valid_necessary:
            valid_necessary = {"$exists": True}
        return cls.db.follow_data.find({f"{direction}_id": id, 'valid': valid_necessary})

    # ????????? ??? ?????? ??? ??????
    # dd.D.db.follow_data.aggregate([{'$group': {'_id': '$from_id', 'count': {'$sum': 1}}}])

    @classmethod
    def follow_data_to_streamers(cls, follow_datas, direction: str, sort_by: str = 'time', reverse: bool = False,
                                 follower_requirements: int = -1) -> Dict[str, List[Dict] | int]:
        start_time = time.time()
        reverse_option = -1 if reverse == (sort_by == 'time') else 1
        counter_direction = 'from' if direction == 'to' else 'to'
        counter_key = f"{counter_direction}_id"
        if sort_by == 'time':
            # converted follow_datas to streamers in 0.17582106590270996s
            # follow_infos = {i[counter_key]: i for i in follow_datas.sort('when', reverse_option)}
            # query = [
            #     {'$match': {'id': {'$in': list(follow_infos.keys())}, 'followers': {'$gte': follower_requirements}}},
            #     {'$addFields': {'__order': {'$indexOfArray': [list(follow_infos.keys()), "$id"]}}},
            #     {'$sort': {'__order': 1}}
            # ]

            # ????????? ?????? ????????? ??????????????? ???????????? ??? ????????? ????????? ??? ?????? ?????? ????????? Streamer??? find ?????????
            # datas = [{'last_updated': i['last_updated'], 'when': i['when'],
            #           'streamer': cls.streamers_data('id', i[counter_key])} for i in
            #          follow_datas.sort('when', reverse_option)]

            # converted follow_datas to streamers in 0.15557217597961426s
            follow_infos = list(follow_datas.sort('when', reverse_option))
            total_follow = len(follow_infos)
            follow_ids = [i[counter_key] for i in follow_infos]
            if follower_requirements != -1:
                streamer_infos = {i['id']: Streamer(i) for i in cls.db.streamers_data.find(
                    {'id': {'$in': follow_ids},
                     'followers': {'$gte': follower_requirements}})}
            else:
                streamer_infos = {i['id']: Streamer(i) for i in cls.db.streamers_data.find(
                    {'id': {'$in': follow_ids}})}
            failed_ids = list(set(follow_ids) - set(streamer_infos))
            datas = [{'valid': i['valid'], 'last_updated': i['last_updated'], 'when': i['when'],
                      'streamer': streamer_infos[i[counter_key]]} for i in follow_infos if
                     i[counter_key] in streamer_infos]
        else:  # elif sort_by == 'follow':
            follow_infos = {i[counter_key]: i for i in follow_datas}
            total_follow = len(follow_infos)
            if follower_requirements != -1:
                query = [
                    {'$match': {'id': {'$in': list(follow_infos.keys())},
                                'followers': {'$gte': follower_requirements}}},
                    {'$sort': {'followers': reverse_option}}
                ]
            else:
                query = [
                    {'$match': {'id': {'$in': list(follow_infos.keys())}}},
                    {'$sort': {'followers': reverse_option}}
                ]

            datas = [{'valid': follow_infos[i['id']]['valid'], 'last_updated': follow_infos[i['id']]['last_updated'],
                      'when': follow_infos[i['id']]['when'],
                      'streamer': Streamer(i)} for i in cls.db.streamers_data.aggregate(query)]
            failed_ids = list(set(follow_infos.keys()) - {i['streamer'].id for i in datas})
        # cls.db.streamers_data.find(
        # {'id': {'$in': list(follow_infos.keys())}, 'followers': {'$gte': follower_requirements}}).sort(
        # 'followers', reverse_option)
        # ????????? ?????? ????????? queue ??? ????????????, ???????????? ?????? ????

        print(f"converted follow_datas to streamers in {time.time() - start_time}s")
        return {'datas': datas, 'total': total_follow, 'failed_ids': failed_ids}

    # ?????? ????????? ?????? ?????? ?????? X, ?????? ?????? ???????????? ????????????
    @classmethod
    def follow_check(cls, from_id, to_id, valid_necessary=True):
        if not valid_necessary:
            valid_necessary = {"$exists": True}
        return cls.db.follow_data.find_one({"from_id": from_id, "to_id": to_id, "valid": valid_necessary})

    @classmethod
    def follow_search(cls, search_by, query, direction, valid_necessary=True):
        id = cls.streamers_data(search_by, query).id
        result = list(cls.follow(id, direction, valid_necessary))
        return result

    @classmethod
    def follow_update_all(cls, datas, streamer_in_interest):
        # ????????? id??? ????????? ???????????? ??????
        # if streamer_in_interest is None:
        #     from_id = datas[0]['from_id']
        # else:
        assert len(set({i['from_id'] for i in datas})) == 1 and (
                not datas or datas[0]['from_id'] == streamer_in_interest.id)
        assert isinstance(streamer_in_interest, Streamer)
        from_id = streamer_in_interest.id
        # assert datas[0]['from_id'] == streamer_in_interest.id
        cls.db.follow_data_information.update_one({'id': from_id}, {'$set': {'id': from_id, 'last_updated': tools.now(),
                                                                             'following_num': len(datas)}}
                                                  , upsert=True)
        updated_ids = [i['to_id'] for i in datas]
        print(f"updating {len(updated_ids)} ids from follow_update_all")
        # Thread(target=cls.update_from_id, args=(updated_ids,)).start()

        # updated_result = cls.follow_update_partial(datas,streamer_in_interest)
        """ $expr:{
                $in:[
                    {
                        "first":"$first",
                        "last":"$last"
                    },
                    [
                        {
                            "first" : "Alice",
                            "last" : "Johnson"
                        },
                        {
                            "first" : "Bob",
                            "last" : "Williams"
                        }
                    ]
                ]
            }"""
        # update many, find and modify ?????? bulk update??? ???????????? ??? ????????? upsert ????????? ????????? ?????? ???
        start_time = time.time()
        cls.db.follow_data.delete_many({'from_id': from_id, 'to_id': {'$in': updated_ids}, 'valid': True})
        # cls.db.follow_data.delete_many({'from_id': from_id, '$expr': {'$in': [{'to_id': '$to_id', 'when': '$when'}, [{'to_id': i['to_id'], 'when': i['when']} for i in datas]]}})
        updated_result = cls.db.follow_data.insert_many(datas)
        deleted_result = cls.db.follow_data.update_many(
            {'from_id': from_id, 'to_id': {'$nin': updated_ids}, 'valid': True},
            {'$set': {'valid': False, 'last_updated': tools.now()}})
        print(f"updating invalid follow took {time.time() - start_time}s")
        # find and modify is deprecated...
        return updated_result, deleted_result

    # ?????? ????????? ?????? ?????? valid False ????????? ?????? ??????
    """
    db.names.find({
        $expr:{
            $in:[
                {
                    "first":"$first",
                    "last":"$last"
                },
                [
                    {
                        "first" : "Alice",
                        "last" : "Johnson"
                    },
                    {
                        "first" : "Bob",
                        "last" : "Williams"
                    }
                ]
            ]
        }
    }).pretty()
    """
    """
            bulk_write_request = [
            UpdateOne({'from_id': data['from_id'], 'to_id': data['to_id'], 'when': data['when']}, {'$set': data},
                      upsert=True) for data in datas]

        # DeleteMany({})
        # InsertOne({'_id': 3}),
        # UpdateOne({'_id': 4}, {'$inc': {'j': 1}}, upsert=True),
        # ReplaceOne({'j': 1}, {'j': 2})])

        result = cls.db.follow_data.bulk_write(bulk_write_request)  # ,projection={'_id':0}
    """

    @classmethod
    def follow_update_partial(cls, datas: List[dict], streamer_in_interest: Streamer):
        # to_ids=[i['to_id'] for i in datas]
        start_time = time.time()
        # bulk_write_request = [
        #     UpdateOne({'from_id': data['from_id'], 'to_id': data['to_id'], 'when': data['when']}, {'$set': data},
        #               upsert=True) for data in datas]
        # cls.db.follow_data.update_many({'from_id':streamer_in_interest.id,'to_id':{'$in':to_ids}})
        # DeleteMany({})
        # InsertOne({'_id': 3}),
        # UpdateOne({'_id': 4}, {'$inc': {'j': 1}}, upsert=True),
        # ReplaceOne({'j': 1}, {'j': 2})])

        # result = cls.db.follow_data.bulk_write(bulk_write_request)  # ,projection={'_id':0}
        # ????????? ?????? in ?????? update many??? ?????? ????????? insert?
        result = []
        for data in datas:
            data['valid'] = True
            result.append(cls.db.follow_data.find_one_and_update(
                {'from_id': data['from_id'], 'to_id': data['to_id'], 'when': data['when']},
                {'$set': data}, upsert=True))  # ,projection={'_id':0}
        print(f"updating follow partially took {time.time() - start_time}s")

        # Thread(target=cls.update_from_id, args=([data['to_id'] for data in datas],)).start()
        return result
        # ?????? ?????? ?????? valid??? true?????? false??? ?????????????????? ???????????? ?????? ?????? ?????? ??????

    @classmethod
    def show_double_ids(cls):
        double_ids = cls.db.streamers_data.aggregate([
            {"$group": {"_id": "$id", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}, "count": {"$gt": 1}}},
            {"$project": {"id": "$_id", "_id": 0}}
        ])
        double_ids = [i['id'] for i in double_ids]
        return double_ids

    @classmethod
    def fix_double_ids(cls):
        double_ids = cls.db.streamers_data.aggregate([
            {"$group": {"_id": "$id", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}, "count": {"$gt": 1}}},
            {"$project": {"id": "$_id", "_id": 0}}
        ])
        double_ids = [i['id'] for i in double_ids]
        for i in double_ids:
            b = list(cls.db.streamers_data.find({'id': i}).sort('last_updated', 1))
            o = Streamer(b[0])
            for j in b[1:]:  # ??????????????? ????????????
                j_id = j['_id']
                del j['_id']
                o.update(j)
                cls.db.streamers_data.delete_one({'_id': j_id})

    @classmethod
    def fix_double_follow_inf(cls):
        double_ids = cls.db.follow_data_information.aggregate([
            {"$group": {"_id": "$id", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}, "count": {"$gt": 1}}},
            {"$project": {"id": "$_id", "_id": 0}}
        ])
        double_ids = [i['id'] for i in double_ids]
        for i in double_ids:
            b = list(cls.db.follow_data_information.find({'id': i}).sort('last_updated', 1))
            first_id = b[0]['_id']
            for j in b[1:]:  # ??????????????? ????????????
                j_id = j['_id']
                del j['_id']
                print(j)
                cls.db.follow_data_information.update_one({'_id': first_id}, {'$set': j})
                cls.db.follow_data_information.delete_one({'_id': j_id})

    @classmethod
    def role_update_all(cls, datas, streamer_in_interest: Streamer):
        start_time = time.time()
        assert isinstance(datas, dict)
        assert isinstance(streamer_in_interest, Streamer)
        broadcaster_id = streamer_in_interest.id

        # assert datas[0]['broadcaster_id'] == streamer_in_interest.id
        cls.db.role_data_information.update_one({'id': broadcaster_id},
                                                {'$set': {'id': broadcaster_id, 'last_updated': tools.now(),
                                                          'vips_num': len(datas['vips']),
                                                          'moderators_num': len(datas['moderators'])}}, upsert=True)
        now = tools.now()
        for role in roles:
            this_data = datas[role]
            if this_data:
                role_ids = [i['id'] for i in this_data]
                cls.db.role_data.delete_many(
                    {'broadcaster_id': broadcaster_id, 'member_id': {'$in': role_ids}, 'valid': True, 'role': role})
                cls.db.role_data.insert_many(
                    [{'broadcaster_id': broadcaster_id, 'member_id': member_id, 'role': role, 'valid': True,
                      'last_updated': now} for member_id in role_ids])
                cls.db.role_data.update_many(
                    {'broadcaster_id': broadcaster_id, 'member_id': {'$nin': role_ids}, 'valid': True, 'role': role},
                    {'$set': {'valid': False, 'last_updated': now}})
        print(f"updating role took {time.time() - start_time}s")
        # find and modify is deprecated...

    def role_update_from_watchers(self, watchers):
        assert isinstance(watchers, dict)
        managers = T.role_adder(watchers)
        # managers=list(set(managers))
        streamers = {}

        viewers = watchers['viewers']
        all_managers = self.role_broadcaster()
        all_managers_login = {D.id_to_login(i['member_id']): i['member_id'] for i in
                              all_managers}
        managers_data = D.update_from_login(managers, skip=True)['data']
        D.get_follower_from_streamers(managers_data, False)
        # assert len(managers_data) == len(managers)
        for role in roles:
            streamers[role] = []
            for i in watchers[role]:
                member = D.streamers_data('login', i)
                streamers[role].append(member)
                member_id = member.id
                D.db.role_data.find_one_and_update(
                    {'broadcaster_id': self.id, 'member_id': member_id},
                    {'$set': {'broadcaster_id': self.id, 'member_id': member_id, 'role': role, 'valid': True,
                              'last_updated': tools.now()}}, upsert=True)  # ,projection={'_id':0}
                # push??? ?????? ?????? ???????
            # D.db.role_data.update_many({'from_id': self.id, 'to_id': {'$in': role_member_id},'role':{'$ne':role}},{'$set': {'valid': False, 'last_updated': tools.now()}})
        fired_managers = set(all_managers_login) & set(viewers)
        fired_ids = [all_managers_login[i] for i in fired_managers]
        D.db.role_data.update_many({'from_id': self.id, 'to_id': {'$in': fired_ids}},
                                   {'$set': {'valid': False, 'last_updated': tools.now()}})
        return streamers

    @classmethod
    def role_data_to_streamers(cls, role_datas, direction: str) -> Dict[str, List[Dict] | int]:
        start_time = time.time()
        counter_direction = 'broadcaster' if direction == 'member' else 'member'
        counter_key = f"{counter_direction}_id"
        managers_infos = {i[counter_key]: i for i in role_datas}
        # ???????????? ????????? ?????? ???
        total_managers = len(managers_infos)
        query = [
            {'$match': {'id': {'$in': list(managers_infos.keys())}}},
            {'$sort': {'followers': -1}}
        ]

        datas = [{'valid': managers_infos[i['id']]['valid'], 'last_updated': managers_infos[i['id']]['last_updated'],
                  'role': managers_infos[i['id']]['role'], 'streamer': Streamer(i)}
                 if 'last_updated' in managers_infos[i['id']]
                 else {'valid': managers_infos[i['id']]['valid'], 'role': managers_infos[i['id']]['role'],
                       'streamer': Streamer(i)}
                 for i in cls.db.streamers_data.aggregate(query)]
        failed_ids = list(set(managers_infos.keys()) - {i['streamer'].id for i in datas})
        # cls.db.streamers_data.find(
        # {'id': {'$in': list(follow_infos.keys())}, 'followers': {'$gte': follower_requirements}}).sort(
        # 'followers', reverse_option)
        # ????????? ?????? ????????? queue ??? ????????????, ???????????? ?????? ????

        print(f"converted role datas to streamers in {time.time() - start_time}s")
        return {'datas': datas, 'total': total_managers, 'failed_ids': failed_ids}


# ????????? id???

# a.db.streamers_data.find({"$text": {"$search": "??????"}},{"score":{"$meta": "textScore"}}).sort({"score":{"$meta":"textScore"}})

"""def ranking_in_lang(lang="ko"):#gt rank??? ??????
    return {k: v for k, v in sorted(
        [i for i in streamers_data.items() if
         'banned' in i[1] and not i[1]['banned'] and i[1]['lang'] == lang and 'ranking' in i[1]],
        key=lambda item: item[1]['ranking'][lang])}
"""

"""db.people.findAndModify({
    query: { name: "Gus", state: "active", rating: 100 },
    sort: { rating: 1 },
    update: { $inc: { score: 1 } },
    upsert: true
})"""

"""db.grades.findOneAndUpdate(
   { "name" : "A. MacDyver" },
   { $inc : { "points" : 5 } },
   { sort : { "points" : 1 }, projection: { "assignment" : 1, "points" : 1 } }
)"""

"""Raising exceptions within __init__() is absolutely fine. There's no other good way to indicate an error condition within an initializer, and there are many hundreds of examples in the standard library where initializing an object can raise an exception.

The error class to raise, of course, is up to you. ValueError is best if the initializer was passed an invalid parameter.
"""


class T:
    header_index = 0
    header = [{} for i in range(len(D.api_key()))]

    @classmethod
    def header_update(cls):
        start_time = time.time()
        for i, client_info in enumerate(D.api_key()):
            response = requests.post(
                f"https://id.twitch.tv/oauth2/token?client_id={client_info['id']}&client_secret={client_info['secret']}&grant_type=client_credentials")
            access_token = json.loads(response.text)['access_token']
            cls.header[i]['client-id'] = client_info['id']
            cls.header[i]['Authorization'] = 'Bearer ' + access_token
        print(f'{len(D.api_key())} header updated and took {time.time() - start_time}s')

    @classmethod
    def twitch_api(cls, url):
        cls.header_index += 1
        try:
            return requests.get(url, headers=cls.header[cls.header_index % len(cls.header)], timeout=20)
        except:
            time.sleep(10)
            return requests.get(url, headers=cls.header[cls.header_index % len(cls.header)])

    @classmethod
    def streams_info_from_login(cls, login):
        url = 'https://api.twitch.tv/helix/streams?user_login=' + login
        try:
            req = cls.twitch_api(url)
            print('get streams info')
            json_data = req.json()
            if len(json_data['data']) == 1:
                on_info = json_data['data'][0]
                on_info['started_at'] = tools.twitch_parse(on_info['started_at'])
                on_info['uptime'] = tools.now() - on_info['started_at']
                return on_info
            else:
                return False
        except Exception as e:
            try:
                print(req.text)
            except:
                print('get failed')
            print("Error checking user: ", e, login)
            return False

    @classmethod
    def streams_info_from_id(cls, id):
        url = 'https://api.twitch.tv/helix/streams?user_id=' + id
        try:
            req = cls.twitch_api(url)
            print('get streams info')
            json_data = req.json()
            if len(json_data['data']) == 1:
                on_info = json_data['data'][0]
                on_info['started_at'] = tools.twitch_parse(on_info['started_at'])
                on_info['uptime'] = tools.now() - on_info['started_at']
                return on_info
            else:
                return False
        except Exception as e:
            try:
                print(req.text)
            except:
                print('get failed')
            print("Error checking user: ", e, id)
            return False

    @classmethod
    def channel_info(cls, broadcaster_id: List[str]):
        assert broadcaster_id
        assert type(broadcaster_id) == list
        result = []
        index = 0
        while index < len(broadcaster_id):
            url = f'https://api.twitch.tv/helix/channels?broadcaster_id={"&broadcaster_id=".join(broadcaster_id[index: index + 100])}'
            result += cls.twitch_api(url).json()['data']
            index += 100
        return result

    @classmethod
    def login_info(cls, login_list: list):
        assert isinstance(login_list, list)
        if not login_list:
            return []
        url = 'https://api.twitch.tv/helix/users?login=' + '&login='.join(login_list)
        res = cls.twitch_api(url).json()
        if not 'data' in res:
            print(login_list)
            raise KeyError
        return res['data']

    @classmethod
    def id_info(cls, id_list: list):
        assert isinstance(id_list, list)
        if not id_list:
            return []
        url = 'https://api.twitch.tv/helix/users?id=' + '&id='.join(id_list)
        return cls.twitch_api(url).json()['data']

    @classmethod
    def add_language_info(cls, datas):
        assert datas
        channel_infos = cls.channel_info([i['id'] for i in datas])
        assert len(datas) == len(channel_infos)
        id_to_lang_dict = {i['broadcaster_id']: i['broadcaster_language'] for i in channel_infos}
        for i in datas:
            i['lang'] = id_to_lang_dict[i['id']]
            i['banned'] = False
            i['created_at'] = tools.twitch_parse(i['created_at'])

    @classmethod
    def streamers_info_api_from_login(cls, login_list):
        start_time = time.time()
        assert isinstance(login_list, list)
        assert tools.is_valid_logins(login_list)
        if not login_list:
            return [], []
        print(len(login_list))
        if '' in login_list:
            tools.remove_all(login_list, '')
        result = []
        index = 0
        while index < len(login_list):
            req = cls.login_info(login_list[index:index + 100])
            if req:
                cls.add_language_info(req)
            result += req
            index += 100
        failed = list(set(login_list) - {i['login'] for i in result})
        print(f"got info of {len(login_list)} logins in {time.time() - start_time}s")
        # unknown and failed, so it can be banned and also failed at the same time
        return result, failed

    @classmethod
    def streamers_info_api_from_id(cls, id_list: List[str]) -> Tuple[List[Dict], List[str]]:
        start_time = time.time()
        assert isinstance(id_list, list)
        if not id_list:
            return [], []
        print(len(id_list))
        result = []
        index = 0
        while index < len(id_list):
            req = cls.id_info(id_list[index:index + 100])
            if req:
                cls.add_language_info(req)
            result += req
            index += 100
        failed = list(set(id_list) - {i['id'] for i in result})
        print(f"got info of {len(id_list)} ids in {time.time() - start_time}s")
        # unknown and failed, so it can be banned and also failed at the same time
        return result, failed

    @classmethod
    def streamers_info_api_from_streamer(cls, streamers_list: List[Streamer]) -> Tuple[List[Dict], List[Streamer]]:
        start_time = time.time()
        assert all(isinstance(i, Streamer) for i in streamers_list)
        reqs, banned_ids = T.streamers_info_api_from_id([i.id for i in streamers_list])
        banned_streamers = [streamer for streamer in streamers_list if streamer.id in banned_ids]
        for streamer in banned_streamers:
            streamer.ban()
        print(f"got info of {len(streamers_list)} streamers from api in {time.time() - start_time}s")
        return reqs, banned_streamers

    @classmethod
    def followed(cls, id, end):
        if end == -1:
            end = float("inf")
        # {'total': 2, 'data': [{'from_id': '465864010', 'from_login': 'nopple8925', 'from_name': 'nopple8925', 'to_id': '160303307', 'to_login': 'musesin', 'to_name': '?????????', 'followed_at'2021-09-09T11:53:37Z'}], 'pagination': {}}
        # ???
        url = f'https://api.twitch.tv/helix/users/follows?to_id={id}&first=100'
        req = cls.twitch_api(url).json()

        total = int(req['total'])
        if total <= end:
            end = total
            ended = True
        else:
            ended = False
        if req['total'] <= 100 and req['total'] != len(req['data']):
            end = 0
        while len(req['data']) < end:
            cursor = req['pagination']['cursor']
            # except:
            #     print(req)
            #     raise ValueError
            url = 'https://api.twitch.tv/helix/users/follows?to_id=' + id + '&first=100&after=' + cursor
            req_temp = cls.twitch_api(url).json()
            req['data'] += req_temp['data']
            req['pagination'] = req_temp['pagination']
            if len(req['data']) > 10000:
                raise OverflowError
        req['data'] = [
            {'when': tools.twitch_parse(i['followed_at']), 'last_updated': tools.now(), 'from_id': i['from_id'],
             'to_id': i['to_id']} for i in req['data']]
        req['ended'] = ended
        # logins_data.update([i['login'] for i in temp_follow])
        return req

    @classmethod
    def following(cls, id, end):
        if end == -1:
            end = float("inf")
        url = f'https://api.twitch.tv/helix/users/follows?from_id={id}&first={min(end, 100)}'
        req = cls.twitch_api(url).json()
        total = int(req['total'])
        if total <= end:
            end = total
            ended = True
        else:
            ended = False
        if req['total'] <= 100 and req['total'] != len(req['data']):
            end = 0
        while len(req['data']) < end:
            cursor = req['pagination']['cursor']
            url = 'https://api.twitch.tv/helix/users/follows?from_id=' + id + '&first=100&after=' + cursor
            req_temp = cls.twitch_api(url).json()
            req['data'] += req_temp['data']
            req['pagination'] = req_temp['pagination']
        req['data'] = [
            {'when': tools.twitch_parse(i['followed_at']), 'last_updated': tools.now(), 'from_id': i['from_id'],
             'to_id': i['to_id'], 'valid': True} for i in req['data']]
        req['ended'] = ended
        # logins_data.update([i['login'] for i in temp_follow])
        return req

    @classmethod
    def role_from_broadcaster(cls, channel):
        data = '[{"operationName":"VIPs","variables":{"login":"%s"},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"612a574d07afe5db2f9e878e290225224a0b955e65b5d1235dcd4b68ff668218"}}}]' % channel
        response = \
            requests.post('https://gql.twitch.tv/gql', headers=headers, data=data).json()[0]['data']['user']['vips'][
                'edges']
        vips_list = [i['node'] for i in response]
        data = '[{"operationName":"Mods","variables":{"login":"%s"},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"cb912a7e0789e0f8a4c85c25041a08324475831024d03d624172b59498caf085"}}}]' % channel
        response = \
            requests.post('https://gql.twitch.tv/gql', headers=headers, data=data).json()[0]['data']['user']['mods'][
                'edges']
        mods_list = [i['node'] for i in response]
        return {'vips': vips_list, 'moderators': mods_list}

    now_working_on_view = []
    temp_view = {}

    @classmethod
    def temp_view_clear(cls, time_interval=60):
        for login in cls.temp_view:
            if time.time() - cls.temp_view[login]['time'] >= time_interval:
                del cls.temp_view[login]

    # ????????????, ?????? ????????? ?????? ????????? ?????? ?????? streamer??? ?????? ?????? ????????? ??????????????? ??????
    # request??? ???????????? ????????? T??? ?????? ??????

    @classmethod
    def view(cls, login):
        now = time.time()
        while login in cls.now_working_on_view and time.time() < now + 100:
            time.sleep(0.5)
        if login in cls.temp_view and (time.time() - cls.temp_view[login]['time']) < 60:
            print(f'used view of {login} from {time.time() - cls.temp_view[login]["time"]}')
            with open('viewlog.txt', 'a') as f:
                f.write(tools.now().strftime("%Y/%m/%d %H:%M:%S"))
            return cls.temp_view[login]['view']
        cls.now_working_on_view.append(login)
        print(cls.now_working_on_view)
        print('view info')
        response = requests.get('https://tmi.twitch.tv/group/user/%s/chatters' % login)

        data = json.loads(response.text)
        data['chatters']['count'] = int(data['chatter_count'])
        cls.temp_view[login] = {
            'view': data['chatters'],
            'time': time.time()}
        tools.remove_all(cls.now_working_on_view, login)
        print(f'view finished {login}')
        print(cls.now_working_on_view)
        return data['chatters']

    @classmethod
    def every_view(cls, login):
        temp_data = cls.view(login)
        return cls.role_adder(temp_data) + temp_data['viewers']

    @classmethod
    def viewer_intersection(cls, streamers_logins):
        intersect = set.intersection(*[set(cls.every_view(streamer_login)) for streamer_login in streamers_logins])
        return list(intersect)

    @classmethod
    def update_bots_list(cls):
        bots_list = {i[0] for i in requests.get('https://api.twitchinsights.net/v1/bots/all').json()['bots']}
        bots_list_online = {i[0] for i in requests.get('https://api.twitchinsights.net/v1/bots/online').json()['bots']}
        D.db.bots_list.update_one({}, {'$set': {'all': list(set(D.bots_list(False)) | bots_list),
                                                'online': list(set(D.bots_list()) | bots_list_online)}}, upsert=True)
        print('updated bots list')

    @classmethod
    def append_bots_list(cls, bots_list: list):
        assert isinstance(bots_list, list)
        D.db.bots_list.update_one({}, {'$set': {'all': list(set(D.bots_list(False)) | set(bots_list)),
                                                'online': list(set(D.bots_list()) | set(bots_list))}}, upsert=True)

    @classmethod
    def role_adder(cls, data: dict):
        assert isinstance(data, dict)
        result = []
        for role in roles:
            result += data[role]
        return result


try:
    D.streamers_search_data_update()
    T.header_update()
    T.update_bots_list()
except:
    print('error')
