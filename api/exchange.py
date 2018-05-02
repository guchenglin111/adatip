
import config

import json
import time
import sqlite3
import requests

class CryptoCompare:

	@staticmethod
	def __get(url, params):
		name = "__get"

		timeout = config.crypto_compare["general_timeout"]
		max_retries = config.crypto_compare["max_retries"]
		retry_backoff = config.crypto_compare["retry_backoff"]

		headers = config.crypto_compare["headers"]

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
					raise Exception("{0} failed: Max {1} retries exceeded".format(name, config.crypto_compare["max_retries"]))
				retries += 1
				time.sleep(retry_backoff*(2**retries))
			else:
				break
		return response


	@staticmethod
	def sync(server_error_count = 0):
		name = "Sync"

		exchangedb = "./api/db/exchange.db"

		currency = "ADA"
		types = "USD,EUR"

		url = config.crypto_compare["base_url"] + "/data/price"
		params = {"fsym" : currency, "tsyms" : types}

		refresh_period = config.crypto_compare["refresh_period"]

		try:
			exdb = sqlite3.connect(exchangedb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		exdbc = exdb.cursor()
		exdbc.execute("SELECT * FROM exchange WHERE _rowid_ = 1")
		db_exchange_data = exdbc.fetchone()
		exdb.commit()

		if db_exchange_data[1] < (time.time() - refresh_period):
			
			try:
				response = CryptoCompare.__get(url, params)
			except Exception as e:
				exdb.close()
				raise Exception("{0} failed: {1} ".format(name, e))

			exchange_data = response.text
			call_time = time.time()

			exdbc.execute("UPDATE exchange SET json = (?), call_time = (?) WHERE _rowid_ = 1", (exchange_data, call_time))
			exdb.commit()

		else:
			exchange_data = db_exchange_data[0]

		exdb.close()
		return json.loads(exchange_data)