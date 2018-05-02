import sqlite3
import requests

def load_mtip_user_ids():
	name = "Load_mtip_user_ids"

	mtipdb = "./models/db/mtip.db"

	try:
		mtdb = sqlite3.connect(mtipdb)
	except Exception as e:
		raise Exception("{0} failed: {1}".format(name, e))

	mtdbc = mtdb.cursor()
	mtdbc.execute("SELECT cw_id, mtip_cad_id FROM mtip")
	
	data = mtdbc.fetchall()
	mtdb.close()

	return data