
import config

import time
import sqlite3

class Backup(object):

	def __init__(self):

		self.save_path = config.backup["save_path"]

		self.mtipdb = "./models/db/mtip.db"
		self.userdb = "./models/db/user.db"

	def db_backup(self):
		name = "Db_backup"

		backup_time = time.time()

		try:
			mtdb = sqlite3.connect(self.mtipdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		with open("{0}mtip-{1}.sql".format(self.save_path, backup_time), "w") as file:
			for line in mtdb.iterdump():
				file.write("{0}\n".format(line))
		mtdb.close()

		try:
			udb = sqlite3.connect(self.userdb)
		except Exception as e:
			raise Exception("{0} failed: {1}".format(name, e))

		with open("{0}user-{1}.sql".format(self.save_path, backup_time), "w") as file:
			for line in udb.iterdump():
				file.write("{0}\n".format(line))
		udb.close()

		return True
