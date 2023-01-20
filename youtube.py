import sys

import requests

sys.setrecursionlimit(10000)
apikey = "AIzaSyDz42Ycduh51gkd7fePmJAkLOVW1lgqdCk"


def justaddress(items):
    res = []
    for j in items:
        if j["id"]["kind"] == "youtube#video":
            try:
                res.append(j["id"]["videoId"])
            except:
                print(j)
                assert False
    return res


def justaddresslist(items):
    res = []
    for j in items:
        if j["snippet"]["resourceId"]["kind"] == "youtube#video":
            try:
                res.append(j["snippet"]["resourceId"]["videoId"])
            except:
                print(j)
                assert False
    return res


def datatovideo(items):
    res = []
    for j in items:
        if j["id"]["kind"] == "youtube#video":
            try:
                res.append(
                    {
                        "id": j["id"]["videoId"],
                        "time": j["snippet"]["publishedAt"],
                        "title": j["snippet"]["title"],
                        "des": j["snippet"]["description"],
                    }
                )
            except:
                print(j)
                assert False
    return res


def datatovideolist(items):
    res = []
    for j in items:
        if j["snippet"]["resourceId"]["kind"] == "youtube#video":
            try:
                res.append(
                    {
                        "id": j["snippet"]["resourceId"]["videoId"],
                        "time": j["snippet"]["publishedAt"],
                        "title": j["snippet"]["title"],
                        "des": j["snippet"]["description"],
                    }
                )

            except:
                print(j)
                assert False
    return res


def statisticsfromusername(username):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/channels?part=statistics&forUsername={username}&key={apikey}"
    ).json()
    return response["items"][0]["statistics"]


def statisticsfromid(channelid):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channelid}&key={apikey}"
    ).json()
    return response["items"][0]["statistics"]


def playlistfromname(username):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forUsername={username}&key={apikey}"
    ).json()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def playlistfromid(channelid):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channelid}&key={apikey}"
    ).json()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def searchid(query):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/search?key={apikey}&part=snippet&part=snippet&type=channel&maxResults=1&q={query}"
    ).json()
    # print(response)
    return (
        response["items"][0]["id"]["channelId"],
        response["items"][0]["snippet"]["title"],
    )


def videodetailfromid(channelid, end=float("inf"), nexttoken=""):
    if end == -1:
        end = float("inf")
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/search?key={apikey}&channelId={channelid}&part=snippet,id&order=date&maxResults=1000000&pageToken={nexttoken}"
    ).json()
    totalnum = response["pageInfo"]["totalResults"]
    video = datatovideo(response["items"])
    if len(video) < 50:
        return video, totalnum
    if end <= 50:
        return video[:end], totalnum
    nexttoken = response["nextPageToken"]
    video = video + videodetailfromid(channelid, end - 50, nexttoken)[0]
    return video, totalnum


def videofromid(channelid, end=float("inf"), nexttoken=""):
    if end == -1:
        end = float("inf")
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/search?key={apikey}&channelId={channelid}&part=snippet,id&order=date&maxResults=1000000&pageToken={nexttoken}"
    ).json()
    totalnum = response["pageInfo"]["totalResults"]
    video = justaddress(response["items"])
    if len(video) < 50:
        return video, totalnum
    if end <= 50:
        return video[:end], totalnum
    nexttoken = response["nextPageToken"]
    video = video + videofromid(channelid, end - 50, nexttoken)[0]
    return video, totalnum


def videodetailfromplaylist(playlistid, end=float("inf"), nexttoken=""):
    if end == -1:
        end = float("inf")
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults=100000&playlistId={playlistid}&key={apikey}&pageToken={nexttoken}"
    ).json()
    video = datatovideolist(response["items"])
    if len(video) < 50:
        return video
    if end <= 50:
        return video[:end]
    nexttoken = response["nextPageToken"]
    video = video + videodetailfromplaylist(playlistid, end - 50, nexttoken)
    return video


def videofromplaylist(playlistid, end=float("inf"), nexttoken=""):
    if end == -1:
        end = float("inf")
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults=100000&playlistId={playlistid}&key={apikey}&pageToken={nexttoken}"
    ).json()
    video = justaddresslist(response["items"])
    if len(video) < 50:
        return video
    if end <= 50:
        return video[:end]
    nexttoken = response["nextPageToken"]
    video = video + videofromplaylist(playlistid, end - 50, nexttoken)
    return video


def videoinfo(videoId):
    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/videos?part=id,snippet,contentDetails,status,statistics&id={videoId}&key={apikey}"
    ).json()
    #    response=requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={videoId}&key={apikey}").json()
    return response


if __name__ == "__main__":
    # print(videofromid(searchid('우왁굳')[0],400))
    print(videofromplaylist(playlistfromname("woowakgood"), end=56))
