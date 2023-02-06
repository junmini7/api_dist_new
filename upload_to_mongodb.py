from pymongo import MongoClient
import pickle
import pymongo
import database_manager as dd
import etc_manager

a = dd.DatabaseHandler()


def load(filename):
    temp = pickle.load(open(filename, "rb"))
    print(f"{filename} loaded")
    return temp


def dump(object, filename):
    pickle.dump(object, open(filename, "wb"))


# {'id': '67708794', 'login': 'nix', 'name': 'Nix', 'when': datetime.datetime(2022, 10, 23, 19, 5, 27), 'last_updated': datetime.datetime(2022, 10, 23, 20, 37, 11, 574842)}
# {'from_id': '49045679', 'from_login': 'woowakgood', 'from_name': '우왁굳', 'to_id': '693895624', 'to_login': 'wakphago', 'to_name': '왁파고_', 'followed_at': 10-01T13:11:39Z'},
client = MongoClient()
db = client.api
streamers_data_file = load("streamers_data.pickle")
following_data_file = load("following_data.pickle")
# refresh_token_dict = load('refresh_token_dict')
client_infos = load("client_infos.pickle")
if not db.api_key.find_one():
    db.api_key.insert_many(client_infos)

if not list(db.logins_data.find()):
    print("upload logins data")
    db.logins_data.insert_one({"data": list(load("logins_data.pickle"))})
if not list(db.follow_data.find()):
    print("upload follow data")
    temp = []
    for i in following_data_file:
        if not i in streamers_data_file:
            print(i)
        else:
            temp += [
                {
                    "from_id": streamers_data_file[i]["id"],
                    "to_id": j["id"],
                    "when": j["when"],
                    "last_updated": j["last_updated"],
                    "valid": True,
                }
                for j in following_data_file[i]
            ]
    print(len(temp))
    print(temp[0])
    db.follow_data.insert_many(temp)
    # a.follow_update_partial(temp)
if not db.follow_data_information.find_one():
    print("update follow data information")
    temp = []
    for i in following_data_file:
        if not i in streamers_data_file:
            print(i)
        elif not following_data_file[i]:
            temp += [
                {
                    "id": streamers_data_file[i]["id"],
                    "last_updated": etc_manager.now(),
                    "following_num": len(following_data_file[i]),
                }
            ]

        else:
            temp += [
                {
                    "id": streamers_data_file[i]["id"],
                    "last_updated": following_data_file[i][0]["last_updated"],
                    "following_num": len(following_data_file[i]),
                }
            ]
    print(len(temp))
    print(temp[0])
    db.follow_data_information.insert_many(temp)

if not db.role_data.find_one():
    print("upload role data")
    temp = []
    for i in streamers_data_file:
        streamer_id = streamers_data_file[i]["id"]
        if "role" in streamers_data_file[i]:
            roles = streamers_data_file[i]["role"]
            for j in roles:
                if not j in streamers_data_file:
                    print(j)
                else:
                    temp.append(
                        {
                            "broadcaster_id": streamers_data_file[j]["id"],
                            "member_id": streamer_id,
                            "role": roles[j],
                            "valid": True,
                        }
                    )
            del streamers_data_file[i]["role"]
    print(temp[0])
    print(len(temp))
    db.role_data.insert_many(temp)
if not list(db.streamers_data.find()):
    print("upload streamers data")
    for i in streamers_data_file:
        try:
            del streamers_data_file[i]["ranking"]
        except:
            pass
    a.streamers_data_insert_many(list(streamers_data_file.values()))
    # db.streamers_data.createIndex({"display_name": 1},
    #                      {"collation": {"locale": 'en', "strength": 2}})
a.streamers_data_rank_refresh()
# db.streamers_data.create_index([("display_name", pymongo.TEXT)])
