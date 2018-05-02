
import config

import logging

class Logger(object):

	def __init__(self):

		self.filename = config.logging["filename"]
		self.save_path = config.logging["save_path"]

		logging.basicConfig(
		format="%(asctime)s [{0}]: %(message)s".format(self.filename),
		datefmt="%m/%d/%Y %I:%M:%S %p",
		level = logging.INFO,
		handlers=[
			logging.FileHandler("{0}/{1}".format(self.save_path, self.filename)),
			logging.StreamHandler()
		])

		logging.info("--LOGGING INITIALIZED--")


	def info(self, string):
		logging.info(string)

