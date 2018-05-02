
import config

import requests
import sqlite3

class Reddit:

	@staticmethod
	def __get(url, params):
		name = "__get"

		timeout = config.reddit["general_timeout"]
		max_retries = config.reddit["max_retries"]
		retry_backoff = config.reddit["retry_backoff"]

		headers = {"Authorization": "bearer {0}".format(Reddit.auth("read"))}
		headers.update(config.reddit["headers"])

		retries = 0
		while 1:
			try:
				response = requests.get(url, params=params, timeout=timeout, headers=headers)
				response.close()
				response.raise_for_status()
			except Exception:
				if response.status_code == requests.codes.unauthorized:
					headers.update({"Authorization": "bearer {0}".format(Reddit.auth("update"))})
					continue
				if not retries < max_retries:
					raise Exception("{0} failed: Max {1} retries exceeded".format(name, config.reddit["max_retries"]))
				retries += 1
				time.sleep(retry_backoff*(2**retries))
			else:
				break
		return response


	@staticmethod
	def __post(url, data, auth = None):
		name = "__post"

		timeout = config.reddit["general_timeout"]
		max_retries = config.reddit["max_retries"]
		retry_backoff = config.reddit["retry_backoff"]

		headers = {"Authorization": "bearer {0}".format(Reddit.auth("read"))}
		headers.update(config.reddit["headers"])

		retries = 0
		while 1:
			try:
				if auth is not None:
					response = requests.post(url, data=data, auth=auth, timeout=timeout, headers=headers)
				else:
					response = requests.post(url, data=data, timeout=timeout, headers=headers)
				response.close()
				response.raise_for_status()
			except Exception:
				if response.status_code == requests.codes.unauthorized:
					headers.update({"Authorization": "bearer {0}".format(Reddit.auth("update"))})
					continue
				if not retries < max_retries:
					raise Exception("{0} failed: Max {1} retries exceeded".format(name, config.reddit["max_retries"]))
				retries += 1
				time.sleep(retry_backoff*(2**retries))
			else:
				break
		return response

	@staticmethod
	def auth(action, server_error_count = 0):
		name = "auth"

		authdb = "./api/db/auth.db"
		actions = {"read" : "READ", "update" : "UPDATE"}

		credentials = config.reddit["credentials"]
		bot_identifier = config.reddit["bot_identifier"]

		try:
			adb = sqlite3.connect(authdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		adbc = adb.cursor()

		if action.upper() == actions["read"]:

			adbc.execute("SELECT token FROM auth WHERE _rowid_ = 1")
			token = adbc.fetchone()[0]
			adb.commit()
			adb.close()

			return token

		elif action.upper() == actions["update"]:

			client_auth = requests.auth.HTTPBasicAuth(bot_identifier["id"], bot_identifier["secret"])

			try:
				response = Reddit.__post(config.reddit["auth_url"], credentials, client_auth)
			except Exception as e:
				adb.close()
				raise Exception("{0} failed: {1}".format(name, e))

			token = response.json()["access_token"]
			adbc.execute("UPDATE auth SET token = (?) WHERE _rowid_ = 1", [token])
			adb.commit()
			adb.close()

			return token

		else:
			adb.close()
			raise Exception("{0} failed: No such action".format(name))

	@staticmethod
	def pm(user, subject, text):
		name = "Pm"

		url = config.reddit["base_url"] + "/api/compose/"

		pm_data = {
		"api_type" : "json",
		"from_sr" : "",
		"subject" : subject,
		"text" : text,
		"to" : user
		}

		Reddit.__post(url, pm_data)

		return True

	@staticmethod
	def inbox(before_post):
		name = "Inbox"

		url = config.reddit["base_url"] + "/message/inbox/"
		#url = "http://127.0.0.1/inbox.json"

		params = {"before" : before_post}
		
		response = Reddit.__get(url, params)

		return(response.json())

	@staticmethod
	def mark_read(thing_ids):
		name = "Mark_read"

		url = config.reddit["base_url"] + "/api/read_message/"

		read_data = {"id" : ",".join(thing_ids)}

		Reddit.__post(url, read_data)

		return True

	@staticmethod
	def reply(thing_id, text, auth = None, server_error_count = 0):
		name = "Reply"

		url = config.reddit["base_url"] + "/api/comment/"

		reply_data = {
		"api_type" : "json",
		"comment" : "",
		"return_rtjson" : "False",
		"text" : text,
		"thing_id" : thing_id
		}

		Reddit.__post(url, reply_data)

		return True

	@staticmethod
	def info(subreddit, thing_id, auth = None, server_error_count = 0):
		name = "Info"
		
		url = config.reddit["base_url"] + "/{0}/api/info/".format(subreddit)

		params = {"id" : thing_id}

		response = Reddit.__get(url, params)

		return response.json()