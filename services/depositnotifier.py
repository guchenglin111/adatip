
import config

import sqlite3
import requests

class DepositNotifier(object):

	def __init__(self):

		self.base_url = config.cardano_node["base_url"]
		self.json_headers = config.cardano_node["json_headers"]

		self.mtip_master_wallet_address = config.microtip["mtip_master_wallet_address"]
		self.mtip_master_account_index = config.cardano_node["default_account_index"]

		self.mtip_read_transaction_limit = config.deposit_notifier["mtip_read_transaction_limit"]
		self.standard_read_transaction_limit = config.deposit_notifier["standard_read_transaction_limit"]

		self.final_deposit_info_ready = False
		self.final_deposit_info = []

		self.txsdb_path = "./services/db/txs.db"
		self.userdb_path = "./models/db/user.db"

		self.last_transaction_time = int(self.__last_transaction_time("read"))
		self.transaction_time_accepted = 0

		self.timeout = config.deposit_notifier["general_timeout"]
		self.response_success = "Right"
		self.response_error = "Left"
		self.verify = False

	def __last_transaction_time(self, action, transaction_time = None):
		name = "__last_transaction_time"

		txsdb = self.txsdb_path

		try:
			txdb = sqlite3.connect(txsdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		txdbc = txdb.cursor()

		if action.upper() == "READ":

			txdbc.execute("SELECT * FROM txs WHERE _rowid_ = 1")
			transaction_time = txdbc.fetchone()
			txdb.close()

			return transaction_time[0]

		elif action.upper() == "UPDATE":

			txdbc.execute("UPDATE txs SET transaction_time = (?) WHERE _rowid_ = 1", [transaction_time])
			txdb.commit()
			txdb.close()

		else:
			txdb.close()
			raise Exception("{0} failed: No such action".format(name))

	def run_scan(self, user_ids):
		name = "Run_scan"

		url = self.base_url + "/api/txs/histories"

		new_last_transaction_time = self.last_transaction_time
		deposit_results = []

		if user_ids[0] == self.mtip_master_wallet_address:
			return

		params = {"walletId" : self.mtip_master_wallet_address, "address" : user_ids[1], "limit" : self.mtip_read_transaction_limit}

		try:
			response = requests.get(url, params=params, timeout=self.timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))
		
		if not self.response_success in response.json():
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]))

		transactions = response.json()[self.response_success][0]

		for transaction in transactions:

			transaction_time = int(round(transaction["ctMeta"]["ctmDate"]))

			if transaction_time > self.last_transaction_time:
				if transaction_time > new_last_transaction_time:
					new_last_transaction_time = transaction_time

				for output in transaction["ctOutputs"]:
					if output[0] == user_ids[1]:
						deposit_results.append({"cw_id" : user_ids[0], "deposit_amount" : output[1]["getCCoin"], "wallet" : "microtip"})

		params = {"walletId" : user_ids[0], "limit" : self.standard_read_transaction_limit}
		
		try:
			response = requests.get(url, params=params, timeout=self.timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not self.response_success in response.json():
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]))

		transactions = response.json()[self.response_success][0]

		for transaction in transactions:

			transaction_time = int(round(transaction["ctMeta"]["ctmDate"]))

			if transaction_time > self.last_transaction_time:

				if transaction_time > new_last_transaction_time:
					new_last_transaction_time = transaction_time

				if not transaction["ctIsOutgoing"]:
					deposit_results.append({"cw_id" : user_ids[0], "deposit_amount" : transaction["ctAmount"]["getCCoin"], "wallet" : "standard"})

		if new_last_transaction_time > self.transaction_time_accepted:
			self.transaction_time_accepted = new_last_transaction_time
			self.__last_transaction_time("update", new_last_transaction_time)

		return deposit_results

	def gather_usernames(self, deposit_results):
		name = "Gather_usernames"
		
		userdb = self.userdb_path

		self.final_deposit_info = []

		try:
			udb = sqlite3.connect(userdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		udbc = udb.cursor()

		for deposit_info_array in deposit_results:
			if deposit_info_array:
				for deposit_info in deposit_info_array:
			
					udbc.execute("SELECT username FROM user WHERE cw_id = (?)", [deposit_info["cw_id"]])
					username = udbc.fetchone()

					self.final_deposit_info.append({"username" : username[0], "deposit_amount" : deposit_info["deposit_amount"], "wallet" : deposit_info["wallet"]})
			
		udb.close()
		deposit_results = None

		self.final_deposit_info_ready = True









