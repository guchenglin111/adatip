
import config

import os
import binascii
import hashlib
import requests

class Mnemonic:

    @staticmethod
    def gen():
        name = "Gen"
        
        fname = "english.txt"

        num_bytes = 16
        base16 = 16
        base2 = 2


        entropy = binascii.b2a_hex(os.urandom(num_bytes)).decode('utf-8')
        entropyHash = binascii.b2a_hex(hashlib.sha256(bytearray.fromhex(entropy)).digest()).decode('utf-8')

        seed = '{:0128b}'.format(int(entropy, base16)) + '{:04b}'.format(int(entropyHash[0], base16))

        try:
            response = requests.get('http://127.0.0.1/{0}'.format(fname), timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise Exception("{0} failed: {1}".format(name, e))
        response.close()

        wordList = response.text.split("\n")

        index = 0
        words = [""]

        for bit in range(0, len(seed)):
            if bit % 11 == 0 and bit != 0:
                index += 1
                words.append("")
            words[index] += seed[bit]

        mnemonic = []

        for value in words:
            mnemonic.append(wordList[int(value, base2)])

        return(" ".join(mnemonic))