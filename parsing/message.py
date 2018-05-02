import config

import models
import parsing

class Message(object):

    def __init__(self, message_data):

        self.message_data = message_data

    def __command_scrub(self):
        name = "__command_scrub"

        empty_string = ""
        space = " "
        new_line = "\n"

        subject_string_list = list(filter(lambda x: x != empty_string, self.message_data["subject"].split(space)))

        body_string_list = list(filter(lambda x: x != empty_string, self.message_data["body"].replace(new_line, space).split(space)))

        return {"subject" : subject_string_list, "body" : body_string_list}

    def command_extract(self):
        name = "Command_extract"

        supported_commands = { "register" : "+REGISTER", "standard_withdrawal" : "+WITHDRAWAL", "mtip_withdrawal" : "+MICROTIP_WITHDRAWAL", "balance" : "+BALANCE", "address" : "+ADDRESS"}
        valid_withdrawal_currency_types = ["ADA", "LOVELACE", "LOVELACES"]
        
        string_list  = self.__command_scrub()

        command = string_list["subject"][0].upper()

        if command in supported_commands.values():
            
            if command == supported_commands["register"]:
                return {"verified_command" : supported_commands["register"]}

            if command == supported_commands["standard_withdrawal"] or command == supported_commands["mtip_withdrawal"]:
                
                try:
                    unverified_amount = string_list["subject"][1]
                except:
                    raise ValueError("{0} failed: Please specify 'amount' parameter".format(name))
                try:
                    currency_type = string_list["subject"][2].upper()
                except:
                    raise ValueError("{0} failed: Please specify 'currency type' parameter. Withdrawal supports ADA or LOVELACE currency types".format(name))

                if not currency_type in valid_withdrawal_currency_types:
                    raise ValueError("{0} failed: Withdrawal only supports ADA or LOVELACE currency types".format(name))

                try:
                    unverified_address = string_list["body"][0]
                except:
                    raise ValueError("{0} failed: Please specify address to withdrawal to".format(name))
    
                try:
                    verified_amount = parsing.general.General.amount_validate(unverified_amount, currency_type = currency_type)
                except ValueError as e:
                    raise ValueError("{0} failed: {1}".format(name, e))

                try:
                    verified_address = models.financial.Financial("").valid_address(unverified_address)
                except ValueError as e:
                    raise ValueError("{0} failed: {1}".format(name, e))

                return {"verified_command" : command, "verified_amount" : verified_amount, "currency_type" : currency_type, "verified_address" : verified_address}

            if command == supported_commands["balance"]:
                return {"verified_command" : supported_commands["balance"]}

            if command == supported_commands["address"]:
                return {"verified_command" : supported_commands["address"]}

        else:
            return False