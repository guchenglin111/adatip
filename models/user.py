
import config

import sqlite3
import requests

import models
import crypto
import api

class User(object):

	def __init__(self, user):

		self.base_url = config.cardano_node["base_url"]
		self.json_headers = config.cardano_node["json_headers"]
		self.default_account_index = config.cardano_node["default_account_index"]
		self.transaction_policy = config.cardano_node["transaction_policy"]
		self.general_timeout = config.cardano_node["general_timeout"]

		self.userdb_path = "./models/db/user.db"
		
		self.response_success = "Right"
		self.response_error = "Left"
		self.verify = False

		self.user = user
		self.user_info = self.lookup()

	def lookup(self):
		name = "Lookup"

		userdb = self.userdb_path

		try:
			udb = sqlite3.connect(userdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		udbc = udb.cursor()
		udbc.execute("SELECT * FROM user WHERE username=(?)", [self.user])
		match = udbc.fetchone()
		udb.commit()
		udb.close()

		if match == None:
			return {"exists" : False}

		else:
			result = {
			"exists" : True,
			"user" : match[0],
			"cw_id" : match[1],
			"cad_id" : match[2],
			"msalt" : match[3],
			}

			return result

	def balance(self):
		name = "Balance"

		url = self.base_url + "/api/wallets/"
		response_format = {"account_amount" : "cwAmount", "balance" : "getCCoin"}

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		try:
			response = requests.get((url + "{0}".format(self.user_info["cw_id"])), timeout=self.general_timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not response.json()[self.response_success]:
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

		return response.json()[self.response_success][response_format["account_amount"]][response_format["balance"]]

	
	def withdrawal(self, amount, address):
		name = "Withdrawal"

		url = self.base_url + "/api/txs/payments/"

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		try:
			balance = self.balance()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if int(amount) > int(balance):
			raise ValueError("{0} failed: Amount {1} (Lovelace) exceeds balance of {2} (Lovelace)".format(name, amount, balance))

		try:
			fee_response = models.financial.Financial(self.user).fee(int(amount), address)
		except ValueError as e:
			raise ValueError("{0} failed: {1}".format(name, e))
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		amount = str(fee_response["amount"])
		
		try:
			response = requests.post((url + "{0}@{1}/{2}/{3}".format(self.user_info["cw_id"], self.default_account_index, address, amount)), timeout=self.general_timeout, json=self.transaction_policy, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		return {"amount" : amount, "fee" : fee_response["fee"]}


	def __find_account_address(self, wallet_id):
		name = "find_account_address"

		url = self.base_url + "/api/accounts/"
		response_format = {"address_list" : "caAddresses", "cad_id" : "cadId"}

		params = {"accountId" : wallet_id}

		try:
			response = requests.get(url, timeout=self.general_timeout, params=params, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not response.json()[self.response_success]:
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

		return response.json()[self.response_success][0][response_format["address_list"]][0][response_format["cad_id"]]

	def register(self):
		name = "Register"

		userdb = self.userdb_path

		url = self.base_url + "/api/wallets/new/"

		if self.user_info["exists"]:
			raise LookupError("{0} failed: User is already registered".format(name))

		try:
			udb = sqlite3.connect(userdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		udbc = udb.cursor()

		try:
			phrase = crypto.mnemonic.gen()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		wallet_data = {
		"cwInitMeta": {
		"cwName": self.user,
		"cwAssurance": "CWAStrict",
		"cwUnit": 0
		},
		"cwBackupPhrase": {
		"bpToList": [phrase]
		}
		}

		try:
			response = requests.post(url, timeout=self.general_timeout, headers=self.json_headers, json=wallet_data, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not response.json()[self.response_success]:
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

		cw_id = response.json()[self.response_success]["cwId"]

		try:
			cad_id = self.__find_account_address(cw_id)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		try:
			mtip_info = models.microtip.Microtip(cw_id).register()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		lookup_info = [self.user, cw_id, cad_id, phrase]
		udbc.execute("INSERT INTO user VALUES (?, ?, ?, ?)", lookup_info)
		udb.commit()
		udb.close()

		return {"cad_id" : cad_id, "mtip_cad_id" : mtip_info["mtip_cad_id"]}

	def delete(self):
		name = "Delete"

		userdb = self.userdb_path
	
		url = self.base_url + "/api/wallets/"

		allowed_delete_balance = 0
		allowed_delete_mtip_balance = 0

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		try:
			udb = sqlite3.connect(userdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		udbc = udb.cursor()

		try:
			user_balance = self.balance()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if int(user_balance) > allowed_delete_balance:
			raise ValueError("{0} failed: Your standard wallet still has a balance of {1} (Lovelace)".format(name, user_balance))

		try:
			response = requests.delete((url + "{0}".format(self.user_info["cw_id"])), timeout=self.general_timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		udbc.execute("DELETE FROM user WHERE username=(?)", [self.user_info["user"]])
		udb.commit()
		udb.close()

		return True
