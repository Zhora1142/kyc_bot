import requests
from eth_account import Account
from tronpy import Tron

Account.enable_unaudited_hdwallet_features()

class Erc:
    def __init__(self, api):
        self.endpoint = 'https://api.etherscan.io/api'
        self.usdt = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
        self.usdc = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
        self.busd = '0x4Fabb145d64652a948d72533023f6E7A623C7C53'
        self.api = api

    def create_wallet(self):
        address, phrase = Account.create_with_mnemonic()
        return address.address, phrase

    def get_transactions(self, contract, address):
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract,
            'address': address,
            'page': 1,
            'offset': 100,
            'startblock': 0,
            'endblock': 99_999_999,
            'sort': 'abc',
            'apikey': self.api
        }
        r = requests.get(self.endpoint, params=params)
        return r.json()

    def get_transaction(self, value, contract, address):
        try:
            transactions = self.get_transactions(contract, address)
        except Exception:
            return None
        else:
            if not transactions['result']:
                return False
            else:
                flag = False
                for i in transactions['result']:
                    v = int(i['value']) / 10 ** int(i['tokenDecimal'])
                    if i['to'] == address.lower() and v >= value - 1:
                        flag = True
                        break

                return flag


class Bsc:
    def __init__(self, api):
        self.endpoint = 'https://api.bscscan.com/api'
        self.usdt = '0x55d398326f99059fF775485246999027B3197955'
        self.usdc = '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'
        self.busd = '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
        self.api = api

    def create_wallet(self):
        address, phrase = Account.create_with_mnemonic()
        return address.address, phrase

    def get_transactions(self, contract, address):
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract,
            'address': address,
            'page': 1,
            'offset': 1000,
            'startblock': 0,
            'endblock': 99_999_999,
            'sort': 'abc',
            'apikey': self.api
        }
        r = requests.get(self.endpoint, params=params)
        return r.json()

    def get_transaction(self, value, contract, address):
        try:
            transactions = self.get_transactions(contract, address)
        except Exception:
            return None
        else:
            if not transactions['result']:
                return False
            else:
                flag = False
                for i in transactions['result']:
                    v = int(i['value']) / 10 ** int(i['tokenDecimal'])
                    if i['to'] == address.lower() and v >= value - 1:
                        flag = True
                        break

                return flag


class Trc:
    def __init__(self):
        self.usdt = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
        self.usdc = 'TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8'

    def create_wallet(self):
        tron = Tron()
        wallet = tron.generate_address()
        return wallet['base58check_address'], wallet['private_key']

    def get_transactions(self, contract, address):
        params = {
            'limit': 200,
            'contract': contract,
            'only_confirmed': True
        }

        r = requests.get(f'https://api.trongrid.io/v1/accounts/{address}/transactions/trc20', params=params)
        return r.json()

    def get_transaction(self, value, contract, address):
        try:
            transactions = self.get_transactions(contract, address)
        except Exception:
            return None
        else:
            if not transactions['data']:
                return False
            else:
                flag = False
                for i in transactions['data']:
                    v = int(i['value']) / 10 ** int(i['token_info']['decimals'])
                    if i['to'] == address and v >= value - 1:
                        flag = True
                        break

                return flag
