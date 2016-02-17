import requests, json, re, os.path, time, urllib

# --------------------------------------------------

# Parameters to change

Login = ""
Password = ""
FilterByCurrentUser = True
GetOnlyRecentSongs = True

# ---------------------------------------------------

SaveGamePath = "savegame.txt"
TimeFormat = "%Y-%m-%dT%H:%M:%S+00:00"
SavedDate = None


class ForumClient:
	_token = None
	_url = "http://241.zuz.sexy"
	_currentUser = None
	
	def __init__ (self,login,password):
		self._login(login, password)
	
	def _login (self, login, password):
		credentials = {"identification":login,"password":password}
		headers = {"Content-Type": "application/vnd.api+json"}
		r = requests.post(self._url+"/api/token", data = json.dumps(credentials), headers = headers)
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
	
	def getDailySongMeta(self):
		headers = {"Content-Type": "application/vnd.api+json", "Authorization":"Token " + self._token}
		r = requests.get(self._url+"/api/discussions/15", headers = headers)
		return json.loads(r.text)
	
	def getPost(self,postId):
		headers = {"Content-Type": "application/vnd.api+json", "Authorization":"Token " + self._token}
		r = requests.get(self._url+"/api/posts/" + postId, headers = headers)
		return json.loads(r.text)
	
	def getLinkToMusicFromPost(self, postId):
		post = self.getPost(postId)
		if (not GetOnlyRecentSongs) or time.strptime(post["data"]["attributes"]["time"],TimeFormat) < SavedDate:
			print "Old shit"
			return None
		if FilterByCurrentUser:
			liked = False
			for like in post["data"]["relationships"]["likes"]["data"]:
				if like["id"] == self._currentUser:
					liked = True
					break
			if (not liked) and post["data"]["relationships"]["user"]["data"]["id"] != self._currentUser:
				return None
		content = post["data"]["attributes"]["content"]
		urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',content)
		url = ""
		for i in reversed(range(0,len(urls))):
			links = re.findall('(?:http.+(?:(?:mp3)|(?:m4a)|(?:wav)))',urls[i])
			if len(links) > 0:
				url = links[-1]
				break
		if url != "":
			return url
		else:
			return None

client = ForumClient(Login,Password)
dailySongMeta = client.getDailySongMeta()
if GetOnlyRecentSongs and os.path.exists(SaveGamePath):
	with open(SaveGamePath,"r") as f:
		SavedDate = time.strptime(f.read(),TimeFormat)
for post in dailySongMeta["data"]["relationships"]["posts"]["data"]:
	link = client.getLinkToMusicFromPost(post["id"])
	if link != None:
		r = requests.get(link)
		print "Saving " + link
		with open(urllib.unquote(link.split("/")[-1]), 'wb') as fd:
			for chunk in r.iter_content(256):
				fd.write(chunk)
with open(SaveGamePath,"w") as f:
	f.write(time.strftime(TimeFormat, time.gmtime()))