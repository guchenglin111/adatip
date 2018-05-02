
import config

import parsing

class Comment(object):

    def __init__(self, comment_data):

        self.bot_names = config.main["bot_names"]
        self.comment_data = comment_data

    def __tip_scrub(self):
        name = "Tip_scrub"

        tip = "tip"
        empty_string = ""
        space = " "
        new_line = "\n"

        string_list = list(filter(lambda x: x != empty_string and x != tip, self.comment_data["body"].replace(new_line, space).split(space)))

        for index in range(0, len(string_list)):
            string_list[index] = string_list[index].replace(new_line, empty_string)

        return string_list

    def tip_extract(self):
        name = "Tip_extract"
        
        valid_currency_abbreviations = ["ADA", "USD", "EUR", "LOVELACE", "LOVELACES"]
        valid_currency_symbols = ["$", "€"]
        valid_symbol_to_currency = { "$" : "USD", "€" : "EUR"}
        
        string_list  = self.__tip_scrub()

        for index, botname in enumerate(self.bot_names):
            try:
                name_location = string_list.index(botname)
            except:
                if index == (len(self.bot_names) - 1):
                    return False
                pass
            else:
                break

        no_match = True

        if no_match:
            try: 
                string_list[name_location - 2]
            except:
                pass
            else:

                if string_list[name_location - 1].upper() in valid_currency_abbreviations:

                    currency_type = string_list[name_location - 1].upper()
                    unverified_amount = string_list[name_location - 2]

                    no_match = False

        if no_match:
            try:
                string_list[name_location - 1]
            except:
                pass
            else:

                if string_list[name_location - 1][0] in valid_currency_symbols:

                    currency_type = valid_symbol_to_currency[string_list[name_location - 1][0]]
                    unverified_amount = string_list[name_location - 1][1:]

                    no_match = False

        if no_match:
            try:
                string_list[name_location + 2]
            except:
                pass
            else:

                if string_list[name_location + 2].upper() in valid_currency_abbreviations:

                    currency_type = string_list[name_location + 2].upper()
                    unverified_amount = string_list[name_location + 1]

                    no_match = False

        if no_match:
            try:
                string_list[name_location + 1]
            except:
                return False
            else:

                if string_list[name_location + 1][0] in valid_currency_symbols:

                    currency_type = valid_symbol_to_currency[string_list[name_location + 1][0]]
                    unverified_amount = string_list[name_location + 1][1:]

                    no_match = False

        if no_match:
            return False

        try:
            verified_amount = parsing.general.General.amount_validate(unverified_amount, currency_type)
        except ValueError as e:
            raise ValueError("{0} failed: {1}".format(name, e))

        results = { "amount" : verified_amount, "currency_type" : currency_type}
        
        return results