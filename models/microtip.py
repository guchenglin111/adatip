
import config

import sqlite3
import requests

import models

class Microtip(object):

	def __init__(self, cw_id):

		self.base_url = config.cardano_node["base_url"]
		self.json_headers = config.cardano_node["json_headers"]
		self.timeout = config.cardano_node["general_timeout"]

		self.master_mtip_wallet_name = config.microtip["master_mtip_wallet_name"]
		self.mtip_master_wallet_address = config.microtip["mtip_master_wallet_address"]
		self.mtip_master_account_index = config.cardano_node["default_account_index"]

		self.mtipdb_path = "./models/db/mtip.db"

		self.ada_multiplier = 10**6
		self.response_success = "Right"
		self.response_error = "Left"
		self.verify = False

		self.withdrawal_amount = None

		self.cw_id = cw_id
		self.user_info = self.lookup()

	def lookup(self):
		name = "Lookup"

		mtipdb = self.mtipdb_path

		try:
			mtdb = sqlite3.connect(mtipdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		mtdbc = mtdb.cursor()
		mtdbc.execute("SELECT * FROM mtip WHERE cw_id=(?)", [self.cw_id])
		
		match = mtdbc.fetchone()

		mtdb.commit()
		mtdb.close()

		if match == None:
			return {"exists" : False}
		else:
			results = {
			"exists" : True,
			"cw_id" : match[0],
			"mtip_cad_id" : match[1],
			"balance_offset_positive" : match[2],
			"balance_offset_negative" : match[3]
			}
			return results

	def __create_mtip_address(self):
		name = "__create_mtip_address"

		url = self.base_url + "/api/addresses/"

		data = "{0}@{1}".format(self.mtip_master_wallet_address, self.mtip_master_account_index)

		try:
			response = requests.post(url, json=data, timeout=self.timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not response.json()[self.response_success]:
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]))

		return (response.json()[self.response_success]["cadId"])


	def register(self):
		name = "Register"

		mtipdb = self.mtipdb_path

		if self.user_info["exists"]:
			raise LookupError("{0} failed: User is already registered".format(name))

		try:
			mtdb = sqlite3.connect(mtipdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		mtdbc = mtdb.cursor()

		try:
			mtip_cad_id = self.__create_mtip_address()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		balance_offset_positive = 0
		balance_offset_negative = 0	

		lookup_info = [self.cw_id, mtip_cad_id, balance_offset_positive, balance_offset_negative]
		mtdbc.execute("INSERT INTO mtip VALUES (?, ?, ?, ?)", lookup_info)
		
		mtdb.commit()
		mtdb.close()

		return {"mtip_cad_id" : mtip_cad_id}

	def balance(self):
		name = "balance"

		url = self.base_url + "/api/txs/histories/"

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		params = {"walletId" : self.mtip_master_wallet_address, "address" : self.user_info["mtip_cad_id"]}

		try:
			response = requests.get(url, params=params, timeout=self.timeout, headers=self.json_headers, verify=self.verify)
			response.close()
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if not self.response_success in response.json():
			raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

		transaction_history = response.json()[self.response_success][0]

		deposits = 0
		for transaction in transaction_history:
			for output in transaction["ctOutputs"]:
				if output[0] == self.user_info["mtip_cad_id"]:
					deposits += int(output[1]["getCCoin"])
		
		balance = deposits + int(self.user_info["balance_offset_positive"]) - int(self.user_info["balance_offset_negative"])

		return balance

	def tip(self, amount, target_cw_id):
		name = "Tip"

		mtipdb = self.mtipdb_path

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		amount = int(amount)

		if amount > int(self.balance()):
			raise ValueError("{0} failed: Amount requested exceeds mtip balance".format(name))

		target_info = Microtip(target_cw_id).user_info

		if not target_info["exists"]:
			raise LookupError("{0} failed: Target user not registered".format(name))

		if target_info == self.user_info:
			raise LookupError("{0} failed: Targer user cannot also be tipping user".format(name))

		try:
			mtdb = sqlite3.connect(mtipdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		mtdbc = mtdb.cursor()

		user_balance_difference = int(self.user_info["balance_offset_positive"]) - int(self.user_info["balance_offset_negative"])

		if user_balance_difference > 0:
			user_balance_offset_positive = user_balance_difference
			user_balance_offset_negative = 0

		elif user_balance_difference < 0:
			user_balance_offset_positive = 0
			user_balance_offset_negative = user_balance_difference * -1

		else:
			user_balance_offset_positive = int(self.user_info["balance_offset_positive"])
			user_balance_offset_negative = int(self.user_info["balance_offset_negative"])

		target_balance_difference = int(target_info["balance_offset_positive"]) - int(target_info["balance_offset_negative"])

		if target_balance_difference > 0:
			target_balance_offset_positive = target_balance_difference
			target_balance_offset_negative = 0

		elif target_balance_difference < 0:
			target_balance_offset_positive = 0
			target_balance_offset_negative = target_balance_difference * -1

		else:
			target_balance_offset_positive = int(target_info["balance_offset_positive"])
			target_balance_offset_negative = int(target_info["balance_offset_negative"])

		mtdbc.execute("UPDATE mtip SET balance_offset_positive=(?), balance_offset_negative=(?) WHERE cw_id=(?)", [str(user_balance_offset_positive), str(user_balance_offset_negative + amount), self.user_info["cw_id"]])
		mtdbc.execute("UPDATE mtip SET balance_offset_positive=(?), balance_offset_negative=(?) WHERE cw_id=(?)", [str(target_balance_offset_positive + amount), str(target_balance_offset_negative), target_info["cw_id"]])
		
		mtdb.commit()
		mtdb.close()

		display_amount = "{0:.6f}".format(float(amount)/self.ada_multiplier)

		results = {"final_amount" : amount, "display_amount" : display_amount}

		return results


	def prepare_withdrawal(self, amount, address):
		name = "Prepare_withdrawal"

		if not self.user_info["exists"]:
			raise LookupError("{0} failed: User not registered".format(name))

		try:
			fee_info = models.financial.Financial(self.master_mtip_wallet_name).fee(amount, address)
		except ValueError as e:
			raise ValueError("{0} failed: {1}".format(name, e))

		balance = int(self.balance())

		if int(amount) > balance:
			raise ValueError("{0} failed: Amount requested {1} (Lovelace) exceeds balance of {2} (Lovelace)".format(name, amount, balance))

		if (int(amount) + int(fee_info["fee"])) > balance:
			raise ValueError("{0} failed: Amount requested {1} (Lovelace) exceeds balance of {2} (Lovelace) when transfer fee of {3} (Lovelace) is added.".format(name, amount, balance, fee_info["fee"]))

		self.withdrawal_amount = int(amount)

		return True

	def finalize_withdrawal(self, final_fee):
		name = "Finalize_withdrawal"

		mtipdb = self.mtipdb_path

		user_balance_offset_negative = int(self.user_info["balance_offset_negative"])

		if not self.withdrawal_amount:
			raise Exception("{0} failed: No withdrawal prepared".format(name))

		final_amount = int(self.withdrawal_amount) + int(final_fee)

		try:
			mtdb = sqlite3.connect(mtipdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		mtdbc = mtdb.cursor()

		mtdbc.execute("UPDATE mtip SET balance_offset_negative=(?) WHERE cw_id=(?)", [str(user_balance_offset_negative + final_amount), self.user_info["cw_id"]])
		
		mtdb.commit()
		mtdb.close()