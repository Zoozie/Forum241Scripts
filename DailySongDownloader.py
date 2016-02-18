import requests
import json
import re
import os.path
import time
import urllib
import collections
import argparse

# --------------------------------------------------

CredentialsFile = "credentials.txt"
SaveGamePath = "savegame.txt"
TimeFormat = "%Y-%m-%dT%H:%M:%S+00:00"
FilterByCurrentUser = False
GetOnlyRecentSongs = False


def load_credentials():
    Credentials = collections.namedtuple("Credentials", ['login', 'password'])
    try:
        with open(CredentialsFile, "r") as f:
            json_cred = json.loads(f.read())
            credentials = Credentials(json_cred["login"], json_cred["password"])
    except:
        print "Create credentials.txt file in JSON format with fields \"login\" and \"password\"!"
        return None
    if credentials.login == "":
        print "Update your credentials file with login and password!"
        return None
    return credentials


class ForumClient:
    _token = None
    _url = "http://241.zuz.sexy"
    _currentUser = None
    _savedDate = None

    def __init__(self, login, password):
        self._login(login, password)

    def _login(self, login, password):
        credentials = {"identification": login, "password": password}
        r = requests.post(self._url + "/api/token", data=json.dumps(credentials), headers=self._get_headers())
        if r.status_code == 200:
            response = json.loads(r.text)
            self._token = response["token"]
            self._currentUser = response["userId"]
            print "Login successful!"
            return True
        else:
            print "Login failed! Server response:"
            print r.status_code, r.text
            return False

    def _get_headers(self):
        headers = {"Content-Type": "application/vnd.api+json"}
        if self._token is not None:
            headers["Authorization"] = "Token " + self._token
        return headers

    def get_daily_song_meta(self):
        r = requests.get(self._url + "/api/discussions/15", headers=self._get_headers())
        return json.loads(r.text)

    def get_post(self, post_id):
        r = requests.get(self._url + "/api/posts/" + post_id, headers=self._get_headers())
        return json.loads(r.text)

    def get_posts(self, post_ids):
        params = {"filter[id]": ",".join(post_ids)}
        r = requests.get(self._url + "/api/posts", headers=self._get_headers(), params=params)
        return json.loads(r.text)["data"]

    def get_link_to_music_from_post(self, post):
        if time.strptime(post["attributes"]["time"], TimeFormat) < self._savedDate:
            print "Old shit, skipping post #" + str(post["attributes"]["number"])
            return None
        if FilterByCurrentUser:
            liked = False
            for like in post["relationships"]["likes"]["data"]:
                if like["id"] == self._currentUser:
                    liked = True
                    break
            if (not liked) and post["relationships"]["user"]["data"]["id"] != self._currentUser:
                return None
        content = post["attributes"]["contentHtml"]
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        url = ""
        for i in reversed(range(0, len(urls))):
            links = re.findall('(?:http.+(?:(?:mp3)|(?:m4a)|(?:wav)))', urls[i])
            if len(links) > 0:
                url = links[-1]
                break
        if url != "":
            return url
        else:
            return None

    def set_saved_date(self, saved_date):
        self._savedDate = saved_date

    def has_saved_date(self):
        return self._savedDate is not None


def print_args():
    changes = ''
    if not FilterByCurrentUser:
        changes = ' not'
    print 'Will' + changes + ' filter by current user'
    changes = ''
    if not GetOnlyRecentSongs:
        changes = ' not'
    print 'Will' + changes + ' get only recent songs'


def main():
    global FilterByCurrentUser, GetOnlyRecentSongs
    # Parsing arguments
    parser = argparse.ArgumentParser(description='Download songs from the Daily Song thread')
    parser.add_argument('--only-recent', action='store_true',
                        help='Show only recent songs (gets state from "' + SaveGamePath + '" file')
    parser.add_argument('--filter-by-cur-user', action='store_true',
                        help='Filter by current user + include every post liked by current user')

    args = parser.parse_args()
    FilterByCurrentUser = args.filter_by_cur_user
    GetOnlyRecentSongs = args.only_recent
    print_args()

    # Main flow
    credentials = load_credentials()
    if credentials is None:
        exit()
    print "Logged in as: " + credentials.login
    client = ForumClient(credentials.login, credentials.password)

    # Restore timestamp
    if GetOnlyRecentSongs:
        if os.path.exists(SaveGamePath):
            with open(SaveGamePath, "r") as f:
                client.set_saved_date(time.strptime(f.read(), TimeFormat))
        else:
            print "You don't have a \"" + SaveGamePath + "\". Will populate all songs"

    # Getting post IDs
    daily_song_meta = client.get_daily_song_meta()
    post_ids = []
    for post in daily_song_meta["data"]["relationships"]["posts"]["data"]:
        post_ids.append(post["id"])
    post_ids.reverse()
    print "Found " + str(len(post_ids)) + " posts"

    # Downloading each song
    for post in client.get_posts(post_ids):
        link = client.get_link_to_music_from_post(post)
        if link is not None:
            r = requests.get(link)
            print "Saving " + link
            with open(urllib.unquote(link.split("/")[-1]), 'wb') as fd:
                for chunk in r.iter_content(256):
                    fd.write(chunk)

    # Saving timestamp
    with open(SaveGamePath, "w") as f:
        f.write(time.strftime(TimeFormat, time.gmtime()))

main()
