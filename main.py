
import config

import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

from multiprocessing.dummy import Pool

import models
import services
import parsing
import api

supported_commands = { "register" : "+REGISTER", "delete" : "+DELETE", "standard_withdrawal" : "+WITHDRAWAL", "mtip_withdrawal" : "+MICROTIP_WITHDRAWAL", "balance" : "+BALANCE", "address" : "+ADDRESS"}
message_types = { "comment" : "t1", "message" : "t4" }
fiat_types = {"usd" : "USD", "eur" : "EUR"}
fiat_symbols = {"USD" : "$", "EUR" : "€"}
user_denomination = "/u/"

failure_counter = 0
time_log = 0
backend_reddit_interactions = 0

mtip_max_tip_display = parsing.general.General().lovelace_to_ada(config.microtip["mtip_max_tip"])
backup_reference_time = time.time()

log = services.logger.Logger()
backup = services.backup.Backup()

log.info("Loading system messages")

response = requests.get("http://127.0.0.1/messages.json", timeout=5)
response.raise_for_status()
system_message = response.json()

log.info("Reading user ids into memory")

inmem_user_ids = services.memload.load_mtip_user_ids()

log.info("Starting deposit notification service")

deposit_notifier_pool = Pool(processes = 1)
deposit_notifier_task = services.depositnotifier.DepositNotifier()
deposit_notifier_pool.map_async(deposit_notifier_task.run_scan, inmem_user_ids, callback=deposit_notifier_task.gather_usernames)

while 1:

    reddit_interactions = 0 + backend_reddit_interactions

    execution_start = time.time()

    last_processed_post = parsing.general.General().last_processed("read")

    log.info("Before : {0}".format(last_processed_post))

    try:
        inbox = api.reddit.Reddit().inbox(last_processed_post)
    except:
        if failure_counter < config.main["max_failure_multiplier"]:
            failure_counter += 1
        log.info("Inbox get failed. Is reddit mad at us? sleeping it off ({0})".format(config.main["failure_sleep_interval"]*failure_counter))
        time.sleep(config.main["failure_sleep_interval"]*failure_counter)
        continue
    else:
    	failure_counter = 0
    reddit_interactions += 1

    inbox_children = inbox["data"]["children"]
    read_posts = []
 
    for child in range(len(inbox_children))[::-1]:
        
        if inbox_children[child]["data"]["new"]:

       	    post_name = inbox_children[child]["data"]["name"]
            read_posts.append(post_name)

            parsing.general.General().last_processed("update", post_name)

            log.info("id {0}".format(post_name))

            time_current = time.time()

            if reddit_interactions and (time_current - time_log) < config.reddit["interaction_time_interval"]*reddit_interactions:
                difference = (config.reddit["interaction_time_interval"]*reddit_interactions) - (time_current - time_log)
                log.info("sleep ({0}) - wait for api limits (reddit_interactions from last update: {1})".format(difference, reddit_interactions))
                time.sleep(difference)
                reddit_interactions = 0

            time_log = time.time()

            if inbox_children[child]["kind"] == message_types["comment"]:

                sender = inbox_children[child]["data"]["author"]

                try:
                    tip = parsing.comment.Comment(inbox_children[child]["data"]).tip_extract()
                except ValueError as e:
                    reddit_interactions += 1
                    api.reddit.Reddit().pm(sender, system_message["title"]["tip_fail"], system_message["text"]["tip_exception"].format(e))
                    continue

                if tip:
                    log.info("tip valid syntax found")

                    sender_account = models.user.User(sender)

                    if not sender_account.user_info["exists"]:
                        reddit_interactions += 1
                        api.reddit.Reddit().pm(sender, system_message["title"]["tip_fail"], system_message["text"]["no_account"])
                        continue

                    subreddit = inbox_children[child]["data"]["subreddit_name_prefixed"]
                    parent_id = inbox_children[child]["data"]["parent_id"]
                    
                    reddit_interactions += 1
                    parent_info = api.reddit.Reddit().info(subreddit, parent_id)

                    reciever = parent_info["data"]["children"][0]["data"]["author"]

                    reciever_account = models.user.User(reciever)

                    if not reciever_account.user_info["exists"]:
                        try:
                            register_info = reciever_account.register()
                            reciever_account.user_info = reciever_account.lookup()
                        except Exception as e:
                            api.reddit.Reddit().mark_read(read_posts)
                            raise Exception(e)
                        auto_register = True
                    else:
                    	auto_register = False
                    
                    sender_financials = models.financial.Financial(sender)
                    ada_amount = sender_financials.convert_to_ada(tip["amount"], tip["currency_type"])

                    mtip_was_possible = False
                    if not int(ada_amount) > config.microtip["mtip_max_tip"]:
                    	
                    	sender_mtip = models.microtip.Microtip(sender_account.user_info["cw_id"])

                    	if not int(ada_amount) > int(sender_mtip.balance()):

                            mtip_tip_data = sender_mtip.tip(ada_amount, reciever_account.user_info["cw_id"])

                            if tip["currency_type"] in fiat_types.values():
                                fiat_currency = tip["currency_type"]
                            else:
                                fiat_currency = fiat_types["usd"]

                            fiat_amount = sender_financials.convert_to_fiat(mtip_tip_data["final_amount"], fiat_currency)

                            reddit_interactions += 1
                            api.reddit.Reddit().reply(parent_id, system_message["text"]["tip_success"].format(user_denomination + reciever, mtip_tip_data["display_amount"], fiat_symbols[fiat_currency], fiat_amount, fiat_currency))

                            if auto_register:
                                inmem_user_ids.append((reciever_account.user_info["cw_id"], register_info["mtip_cad_id"]))
                                reddit_interactions += 1
                                api.reddit.Reddit().pm(reciever, system_message["title"]["auto_register"], system_message["text"]["auto_register"].format(mtip_tip_data["display_amount"], register_info["cad_id"], mtip_max_tip_display, register_info["mtip_cad_id"]))
                            continue
                    	else:
                    		mtip_was_possible = True

                    try:
                        tip_data = sender_financials.tip(ada_amount, reciever)
                    except ValueError as e:
                        if auto_register:
                            reciever_account.delete()
                        reddit_interactions += 1
                        api.reddit.Reddit().pm(sender, system_message["title"]["tip_fail"], system_message["text"]["tip_exception"].format(e))
                        continue
                    except Exception as e:
                        api.reddit.Reddit().mark_read(read_posts)
                        raise Exception(e)
                    
                    reply_text = system_message["text"]["tip_success"]

                    if mtip_was_possible:
                        reply_text = reply_text + system_message["special"]["mtip_possible"]
                    
                    if tip_data["subtract_fee_from_amount"]:
                        reply_text = reply_text + system_message["special"]["fee_from_amount"]

                    if tip["currency_type"] in fiat_types.values():
                        fiat_currency = tip["currency_type"]
                    else:
                        fiat_currency = fiat_types["usd"]

                    fiat_amount = sender_financials.convert_to_fiat(tip_data["final_amount"], fiat_currency)
                    
                    reddit_interactions += 1
                    api.reddit.Reddit().reply(parent_id, reply_text.format(user_denomination + reciever, tip_data["display_amount"], fiat_symbols[fiat_currency], fiat_amount, fiat_currency))

                    if auto_register:
                        inmem_user_ids.append((reciever_account.user_info["cw_id"], register_info["mtip_cad_id"]))
                        reddit_interactions += 1
                        api.reddit.Reddit().pm(reciever, system_message["title"]["auto_register"], system_message["text"]["auto_register"].format(tip_data["display_amount"], register_info["cad_id"], mtip_max_tip_display, register_info["mtip_cad_id"]))
                    continue

            elif inbox_children[child]["kind"] == message_types["message"]:

                user = inbox_children[child]["data"]["author"]
                
                try:
                    command = parsing.message.Message(inbox_children[child]["data"]).command_extract()
                except ValueError as e:
                    reddit_interactions += 1
                    api.reddit.Reddit().pm(user, system_message["title"]["command_fail"], system_message["text"]["command_exception"].format(e))
                    continue

                if command:
                    log.info("command valid syntax found")

                    user_account = models.user.User(user)

                    if command["verified_command"] == supported_commands["register"]:
                        
                        if user_account.user_info["exists"]:
                            reddit_interactions += 1
                            api.reddit.Reddit().pm(user, system_message["title"]["command_fail"], system_message["text"]["already_registered"].format(user_account.user_info["cad_id"], mtip_max_tip_display, models.microtip.Microtip(user_account.user_info["cw_id"]).user_info["mtip_cad_id"]))
                            continue

                        register_info = user_account.register()
                        user_account.user_info = user_account.lookup()

                        inmem_user_ids.append((user_account.user_info["cw_id"], register_info["mtip_cad_id"]))
                        reddit_interactions += 1
                        api.reddit.Reddit().pm(user, system_message["title"]["normal_register"], system_message["text"]["register_success"].format(register_info["cad_id"], mtip_max_tip_display, register_info["mtip_cad_id"]))
                        continue

                    if not user_account.user_info["exists"]:
                        reddit_interactions += 1
                        api.reddit.Reddit().pm(user, system_message["title"]["command_fail"], system_message["text"]["no_account"])
                        continue
                    
                    if command["verified_command"] == supported_commands["standard_withdrawal"]:

                        user_financials = models.financial.Financial(user)

                        try:
                            ada_amount = user_financials.convert_to_ada(command["verified_amount"], command["currency_type"])
                        except Exception as e:
                            api.reddit.Reddit().mark_read(read_posts)
                            raise Exception(e)
                        try:
                            user_account.withdrawal(ada_amount, command["verified_address"])
                        except ValueError as e:
                            reddit_interactions += 1
                            api.reddit.Reddit().pm(user, system_message["title"]["withdrawal_fail"], system_message["text"]["command_exception"].format(e))
                            continue
                        except Exception as e:
                            api.reddit.Reddit().mark_read(read_posts)
                            raise Exception(e)

                        display_balance = parsing.general.General().lovelace_to_ada(ada_amount)

                        reddit_interactions += 1
                        api.reddit.Reddit().pm(user, system_message["title"]["withdrawal_success"], system_message["text"]["withdrawal_success"].format(display_balance, user_account.user_info["cad_id"], command["verified_address"]))
                        continue

                    elif command["verified_command"] == supported_commands["mtip_withdrawal"]:

                    	user_financials = models.financial.Financial(user)

                    	try:
                    		ada_amount = user_financials.convert_to_ada(command["verified_amount"], command["currency_type"])
                    	except Exception as e:
                    		api.reddit.Reddit().mark_read(read_posts)
                    		raise Exception(e)

                    	user_mtip = models.microtip.Microtip(user_account.user_info["cw_id"])
                   
                    	try:
                    		user_mtip.prepare_withdrawal(ada_amount, command["verified_address"])
                    	except ValueError as e:
                    		reddit_interactions += 1
                    		api.reddit.Reddit().pm(user, system_message["title"]["withdrawal_fail"], system_message["text"]["command_exception"].format(e))
                    		continue  
                    	try:
                    		withdrawal_info = models.user.User(config.microtip["master_mtip_wallet_name"]).withdrawal(ada_amount, command["verified_address"])
                    	except Exception as e:
                    		api.reddit.Reddit().mark_read(read_posts)
                    		raise Exception(e)
                    	try:
                    		user_mtip.finalize_withdrawal(withdrawal_info["fee"])
                    	except Exception as e:
                    		api.reddit.Reddit().mark_read(read_posts)
                    		raise Exception(e)

                    	display_balance = parsing.general.General().lovelace_to_ada(ada_amount)

                    	reddit_interactions += 1
                    	api.reddit.Reddit().pm(user, system_message["title"]["withdrawal_success"], system_message["text"]["microtip_withdrawal_success"].format(display_balance, user_mtip.user_info["mtip_cad_id"], command["verified_address"]))
                    	continue
                        
                    elif command["verified_command"] == supported_commands["balance"]:
                        
                        try:
                            standard_balance = user_account.balance()
                        except Exception as e:
                            api.reddit.Reddit().mark_read(read_posts)
                            raise Exception(e)

                        mtip_balance = models.microtip.Microtip(user_account.user_info["cw_id"]).balance()

                        standard_display_balance = parsing.general.General().lovelace_to_ada(standard_balance)
                        mtip_display_balance = parsing.general.General().lovelace_to_ada(mtip_balance)

                        reddit_interactions += 1
                        api.reddit.Reddit().pm(user, system_message["title"]["balance"], system_message["text"]["balance"].format(standard_display_balance, mtip_display_balance))
                        continue

                    elif command["verified_command"] == supported_commands["address"]:

                    	reddit_interactions += 1
                    	api.reddit.Reddit().pm(user, system_message["title"]["address"], system_message["text"]["address"].format(user_account.user_info["cad_id"], mtip_max_tip_display, models.microtip.Microtip(user_account.user_info["cw_id"]).user_info["mtip_cad_id"]))
                    	continue
                else:
                    reddit_interactions +=1
                    api.reddit.Reddit().pm(user, system_message["title"]["command_not_understood"], system_message["text"]["command_not_understood"])
                    continue

    backend_reddit_interactions = 0

    if read_posts:
        
        backend_reddit_interactions += 1
        api.reddit.Reddit().mark_read(read_posts)

    if execution_start > (backup_reference_time + config.backup["backup_interval"]):
        
        log.info("Creating backup of user related databases (backup_interval {0} seconds)".format(config.backup["backup_interval"]))
        backup_reference_time = execution_start
        backup.db_backup()

    if deposit_notifier_task.final_deposit_info_ready:

        for deposit_info in deposit_notifier_task.final_deposit_info:

            log.info("sending deposit notification")

            desposit_display_amount = parsing.general.General().lovelace_to_ada(deposit_info["deposit_amount"])

            backend_reddit_interactions += 1
            api.reddit.Reddit().pm(deposit_info["username"], system_message["title"]["deposit_recieved"], system_message["text"]["deposit_recieved"].format(desposit_display_amount, deposit_info["wallet"]))
    
        deposit_notifier_task = services.depositnotifier.DepositNotifier()
        deposit_notifier_pool.map_async(deposit_notifier_task.run_scan, inmem_user_ids, callback=deposit_notifier_task.gather_usernames)
        
    execution_time = (time.time() - execution_start)
    if not execution_time > config.main["sleep_interval"]:

        time_difference = config.main["sleep_interval"] - execution_time

        if backend_reddit_interactions > int(time_difference):
            backend_reddit_interactions = int(backend_reddit_interactions - time_difference)
        else:
            backend_reddit_interactions = 0

        log.info("sleep time ({0:.02f})".format(time_difference))
        time.sleep(time_difference)