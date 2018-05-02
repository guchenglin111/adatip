
main = dict(
	bot_names = ["/u/adatip", "/u/adatip/", "u/adatip", "u/adatip/"],
	sleep_interval = 18, # minimum time between checking bot's inbox
	failure_sleep_interval = 5, 
	max_failure_multiplier = 180,
	)

cardano_node = dict(
	base_url = "https://127.0.0.1:8090",
	transaction_policy = {"groupingPolicy" : "OptimizeForHighThroughput"}, # OptimizeForSecurity is the other option available
	default_account_index = 2147483648,
	json_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'},
	general_timeout = 30,
	)

reddit = dict(
	headers = {"User-Agent": "web:beta.adatip:V0.9.8 (by /u/geitir)"},
	base_url = "https://oauth.reddit.com",
	auth_url = "https://www.reddit.com/api/v1/access_token",
	max_retries = 10,
	retry_backoff = 0.1,
	general_timeout = 10,
	credentials = {
		"grant_type" : "password",
		"username" : "",
		"password" : ""
		},
	bot_identifier = {
		"id" : "",
		"secret" : ""
		},
	interaction_time_interval = 1, # reddit allows 60 interactions a minute, so 1 interaction per second. I wouldn't change this
	)

crypto_compare = dict(
	headers = {"User-Agent": "web:reddit:beta.adatip:V0.9.8 (by /u/geitir)"},
	base_url = "https://min-api.cryptocompare.com",
	refresh_period = 20, # time between updating exchange rate
	max_retries = 10,
	retry_backoff = 0.1,
	general_timeout = 10,
	)

microtip = dict(
	master_mtip_wallet_name = "~mtip~", # contains the character ~ since reddit doesn't allow it and therefore the name can never conflict with a user
	mtip_master_wallet_address = "", # address for the mtip wallet 
	mtip_max_tip = 5*10**6, # in Lovelace
	)

deposit_notifier = dict(
	mtip_read_transaction_limit = 3, # how many transactions to lookup to check for new deposits (mtip wallet, user unique address specific)
	standard_read_transaction_limit = 3, # how many transactions to lookup to check for new deposits (user individual wallet)
	)

logging = dict(
	save_path = "./",
	filename = "adatip.log",
	)

backup = dict(
	save_path = "./backups/",
	backup_interval = 3600,
	)
