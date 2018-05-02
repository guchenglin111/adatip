
import config

import requests

import models
import api


class Financial(object):

	def __init__(self, user):

		self.base_url = config.cardano_node["base_url"]
		self.policy = config.cardano_node["transaction_policy"]
		self.default_account_index = config.cardano_node["default_account_index"]
		self.headers = config.cardano_node["json_headers"]
		self.timeout = config.cardano_node["general_timeout"]

		self.verify = False
		self.ada_multiplier = 10**6
		self.response_success = "Right"
		self.response_error = "Left"

		self.user = user

	def convert_to_ada(self, amount, currency_type):
		name= "Convert_to_ada"

		currency_dict = {"ada" : "ADA", "usd" : "USD", "eur" : "EUR", "lovelace" : "LOVELACE", "lovelaces" : "LOVELACES"}
		exchange_currencies = ["USD", "EUR"]

		amount = float(amount)
		currency_type = currency_type.upper()

		if not currency_type in currency_dict.values():
			raise Exception("{0} failed: Invalid currency type".format(name))

		if currency_type == currency_dict["lovelace"] or currency_type == currency_dict["lovelaces"]:
			return str(int(amount))

		if currency_type == currency_dict["ada"]:
			return str(int(amount * self.ada_multiplier))

		try:
			exchange_data = api.exchange.CryptoCompare.sync()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if currency_type in exchange_currencies:

			try:
				value = float((amount/exchange_data[currency_type]))
			except:
				raise Exception("{0} failed: Unexpected exchange currency symbol error".format(name))

			value = str(int((float("{0:.6f}".format(value)) * self.ada_multiplier)))

			return value

	def convert_to_fiat(self, amount, currency_type):
		name = "Convert_to_fiat"

		exchange_currencies = ["USD", "EUR"]

		amount = int(amount)

		try:
			exchange_data = api.exchange.CryptoCompare.sync()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if currency_type.upper() in exchange_currencies:

			value = float((amount/self.ada_multiplier)*exchange_data[currency_type])

			return "{0:.8f}".format(value)

	def valid_address(self, address):
		name = "Valid_address"

		url = self.base_url + "/api/addresses/"

		try:
			response = requests.get((url + "{0}/".format(address)), timeout=self.timeout, headers=self.headers, verify=self.verify)
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))
		response.close()

		if not response.json()[self.response_success]:
			raise ValueError("{0} failed: Address is not valid".format(name))
		else:
			return address


	def fee(self, amount, address):
		name = "Fee"

		url = self.base_url + "/api/txs/fee/"
		response_format = {"fee" : "getCCoin"}

		recursive_keyword = "not enough money"
		fee = 0
		subtract_fee_from_amount = False

		user = models.user.User(self.user)
		
		if not user.user_info["exists"]:
			raise Exception("{0} failed: User not registered".format(name))

		try:
			balance = user.balance()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if int(balance) < int(amount):
			raise ValueError("{0} failed: Amount exceeds balance".format(name))

		try:
			response = requests.post((url + "{0}@{1}/{2}/{3}".format(user.user_info["cw_id"], str(self.default_account_index), address, str(amount))), timeout=self.timeout, json=self.policy, headers=self.headers, verify=self.verify)
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))
		response.close()

		fee_response = response.json().copy()

		if not self.response_success in fee_response:

			if recursive_keyword in fee_response[self.response_error]["contents"]:

				amount = int(balance)

				while not self.response_success in fee_response:

					try:
						response = requests.post((url + "{0}@{1}/{2}/{3}".format(user.user_info["cw_id"], self.default_account_index, address, amount)), timeout=self.timeout, json=self.policy, headers=self.headers, verify=self.verify)
						response.raise_for_status()
					except Exception as e:
						raise Exception("{0} failed: {1}".format(name, e))
					response.close()

					fee_response = response.json().copy()

					if self.response_error in fee_response:

						if recursive_keyword in fee_response[self.response_error]["contents"]:

							subtract_fee_from_amount = True
							fee = int("".join(filter(str.isdigit, fee_response[self.response_error]["contents"])))
							amount = amount - fee

							if amount <= 0:
								raise ValueError("{0} failed: Insufficient balance of {1} (Lovelace) for base fee of {2} (Lovelace)".format(name, balance, fee))
						else:
							raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

			else:
				raise Exception("{0} failed: {1}".format(name, response.json()[self.response_error]["contents"]))

		final_fee = fee_response[self.response_success][response_format["fee"]]

		if int(amount) < int(final_fee):
			raise ValueError("{0} failed: Transfer fee of {1} (Lovelace) is larger than amount requested to be sent of {2} (Lovelace)".format(name, final_fee, amount))

		results = {"amount" : amount, "fee" : final_fee, "subtract_fee_from_amount" : subtract_fee_from_amount}

		return results

	def tip(self, amount, target_user):
		name = "Tip"

		url = self.base_url + "/api/txs/payments/"

		user = models.user.User(self.user)
		
		if not user.user_info["exists"]:
			raise Exception("{0} failed: User not registered".format(name))

		target = models.user.User(target_user)
		
		if not target.user_info["exists"]:
			raise Exception("{0} failed: Target not registered".format(name))

		try:
			balance = user.balance()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		if int(balance) < int(amount):
			raise ValueError("{0} failed: Amount requested exceeds balance".format(name))

		try:
			fee_results = financial(self.user).fee(int(amount), target.user_info["cad_id"])
		except ValueError as e:
			raise ValueError("{0} failed: {1}".format(name, e))
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		amount = fee_results["amount"]
		display_amount = "{0:.6f}".format(float(amount)/self.ada_multiplier)
		
		try:
			response = requests.post((url + "{0}@{1}/{2}/{3}".format(user_info["cw_id"], self.default_account_index, target.user_info["cad_id"], amount)), timeout=self.timeout, json=self.policy, headers=self.headers, verify=self.verify)
			response.raise_for_status()
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))
		response.close()
		
		results = {"final_amount" : amount, "display_amount" : display_amount, "fee" : fee_results["fee"], "subtract_fee_from_amount" : fee_results["subtract_fee_from_amount"]}

		return results
