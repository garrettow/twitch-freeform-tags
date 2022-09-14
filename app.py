import json
import os
import requests
from dotenv import load_dotenv
import threading

load_dotenv()

def sortDict(dict):
    return {k: v for k, v in sorted(dict.items(), key=lambda item: item[1], reverse=True)}

def fixDict(d):
    arr = []
    for key in d:
        arr.append({
            "name": key,
            "streamer_count": d[key]["streamer_count"],
            "viewer_count": d[key]["viewer_count"]
        })

    return arr

class TwitchOfficialApi():
    CLIENT_ID = os.getenv("CLIENT_ID")
    SECRET = os.getenv("SECRET")

    streams = []

    def __init__(self, amount):
        self.amount = amount
        pass

    def setAccessToken(self):
        response = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={self.CLIENT_ID}&client_secret={self.SECRET}&grant_type=client_credentials")
        self.accessToken = response.json()["access_token"]

    def fetch(self, pag = None):
        self.setAccessToken()

        while len(self.streams) <= self.amount:
            p = self.getStreams(pag)
            print(len(self.streams))
            self.fetch(p)
        
        return self.streams

    def getIdsMap(self, n):
        print(n["viewer_count"])
        return (n["user_login"], n["viewer_count"])


    def getStreams(self, pag):
        params = None

        if pag:
            params = {"first": 100, "language": "en", "after": pag}
        else:
            params = {"first": 100, "language": "en",}

        headers = {"Authorization": f"Bearer {self.accessToken}", "Client-Id": self.CLIENT_ID}

        response = requests.get("https://api.twitch.tv/helix/streams", params=params, headers=headers)

        users = list(map(self.getIdsMap, response.json()["data"]))

        p = response.json()["pagination"]["cursor"]

        self.streams.extend(users)

        return p

    pass

class TwitchGqlFreeFormTags():
    TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
    
    total = {}

    def __init__(self, users):
        self.users = users

    def filterMap(self, n):
        return n["name"]

    def request(self, thread_group):
        print("thread started request")
        for user in thread_group:
            saw = []

            headers = {"Client-Id": self.TWITCH_CLIENT_ID}

            lol = [{"operationName":"RealtimeStreamTagList","variables":{"channelLogin":user[0],"freeformTagsEnabled": True},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"6affddbb45d547bd7a071d80086c4f383aba728e16d6080b42e6a5442880a270"}}}]

            response = requests.post("https://gql.twitch.tv/gql", headers=headers, json=lol)

            """ f response.json()[0]["data"]["currentUser"] == None """
            if response.json()[0]["data"]["user"]["stream"] == None:
                continue

            tagsMapped = list(map(self.filterMap, response.json()[0]["data"]["user"]["stream"]["freeformTags"]))

            for tag in tagsMapped:
                if tag in saw:
                    continue
                saw.append(tag)
                if self.total.get(tag) == None:
                    self.total[tag] = {}
                    self.total[tag]["viewer_count"] = user[1]
                    self.total[tag]["streamer_count"] = 1
                else:
                    self.total[tag]["viewer_count"] += user[1]
                    self.total[tag]["streamer_count"] += 1

        print("thread finished")    

    def fetch(self):

        #create thread groups

        thread_size = round(len(self.users) / 20)

        thread_groups = []
        current_thread_group = []

        for user in self.users:
            if len(current_thread_group) <= thread_size:
                current_thread_group.append(user)
            else:
                thread_groups.append(current_thread_group)
                current_thread_group = []

        if len(current_thread_group) > 0:
            thread_groups.append(current_thread_group)

        threads = list()

        for t in range(len(thread_groups)):
            x = threading.Thread(target=self.request, args=(thread_groups[t], ))
            threads.append(x)
            x.start()

        for thread in threads:
            thread.join()
        
        return self.total

class Main():

    def __init__(self):
        pass

    def run(self):

        twitchOfficialApi = TwitchOfficialApi(1000)
        users = twitchOfficialApi.fetch() #fetches user names of X amount of streams
    
        print(users)

        gql = TwitchGqlFreeFormTags(users)
        result = gql.fetch()

        with open("tags.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(fixDict(result)))


main = Main()
main.run()