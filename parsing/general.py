
import config

import sqlite3

class General():
    
    @staticmethod
    def lovelace_to_ada(amount):

        ada_multiplier = 10**6
        display_amount = "{0:.6f}".format(float(amount)/ada_multiplier)

        return display_amount

    @staticmethod
    def amount_validate(amount, currency_type):
        name = "Amount_validate"

        ellipse = "."
        invalid_float_abbreviations = ["LOVELACE", "LOVELACES"]

        valid_standard_decimal_sig_figs = 6
        valid_standard_integer_sig_figs = 6
        valid_nonfloat_integer_sig_figs = 12

        try:
            float(amount)
        except:
            raise ValueError("{0} failed: Couldn't validate amount input".format(name))

        try:
            ellipse_location = amount.index(ellipse)
        except:
            pass
        else:
            if currency_type in invalid_float_abbreviations:
                raise ValueError("{0} failed: Float type invalid for lovelace".format(name))

            decimal_location = (ellipse_location + 1)
            integer_location = ellipse_location

            if len(amount[decimal_location:]) > valid_standard_decimal_sig_figs:
                raise ValueError("{0} failed: Only {1} decimal places valid".format(name, valid_standard_decimal_sig_figs))

            if len(amount[:integer_location]) > valid_standard_integer_sig_figs:
                raise ValueError("{0} failed: Only {1} numeric places valid (in non lovelace)".format(name, valid_standard_integer_sig_figs))

            decimal_split = list(filter(None, amount.split(".")))

            try:
                for side in decimal_split:
                    int(side)
            except:
                raise ValueError("{0} failed: Couldn't validate amount input".format(name))

            return amount

        if currency_type in invalid_float_abbreviations:
            if len(amount) > valid_nonfloat_integer_sig_figs:
                raise ValueError("{0} failed: Only {1} numeric places valid (in lovelace)".format(name, valid_nonfloat_integer_sig_figs))

        elif len(amount) > valid_standard_integer_sig_figs:
            raise ValueError("{0} failed: Only {1} numeric places valid (in non lovelace)".format(name, valid_standard_integer_sig_figs))

        try:
            int(amount)
        except:
            raise ValueError("{0} failed: Couldn't validate amount input".format(name))

        return amount

    @staticmethod
    def last_processed(action, post_id = None):
        name = "Last_processed"

        inboxdb = "./parsing/db/inbox.db"

        actions = {"read" : "READ", "update" : "UPDATE"}

        try:
            idb = sqlite3.connect(inboxdb)
        except Exception as e:
            raise Exception("{0} failed: {1}".format(name, e))

        idbc = idb.cursor()

        if action.upper() == actions["read"]:

            idbc.execute("SELECT last_post FROM inbox WHERE _rowid_ = 1")

            post_id = idbc.fetchone()[0]

            idb.commit()
            idb.close()

            return post_id

        elif action.upper() == actions["update"]:
            if not post_id:
                raise Exception("{0} failed: No post_id provided")

            idbc.execute("UPDATE inbox SET last_post = (?) WHERE _rowid_ = 1", [post_id])
            idb.commit()
            idb.close()

        else:
            idb.close()
            raise Exception("{0} failed: No such action".format(name))