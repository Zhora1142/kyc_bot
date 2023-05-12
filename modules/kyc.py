from configparser import ConfigParser
from modules.sql import MysqlCollector
from copy import copy

config = ConfigParser()
config.read('config.ini')

sql = MysqlCollector(**config['sql'])


def select(**kwargs):
    sql_copy = copy(sql)
    result = sql_copy.select(**kwargs)
    del sql_copy
    return result


def get_platform_list():
    data = select(table='platforms')['data']
    if not isinstance(data, list):
        data = [data]

    return [Platform(platform_id=i['id'], name=i['name']) for i in data]


def get_platform_by_id(platform_id):
    data = select(table='platforms', where=f'id={platform_id}')['data']
    if data:
        return Platform(platform_id=platform_id, name=data['name'])
    else:
        return None


def get_accounts_by_platform_id(platform_id):
    data = select(table='account_types', where=f'platform={platform_id}')['data']
    if not isinstance(data, list):
        data = [data]

    return [Account(account_id=i['id'], platform_id=platform_id, name=i['name'], price=i['price'], min_price=i['min_price'], description=i['description']) for i in data]


def get_account_by_id(account_id):
    data = select(table='account_types', where=f'id={account_id}')['data']
    if data:
        return Account(account_id=account_id, platform_id=data['platform'], name=data['name'], price=data['price'], min_price=data['min_price'], description=data['description'])
    else:
        return None


def create_platform(name):
    sql.insert(table='platforms', data={'name': name})


def create_account(data):
    sql.insert(table='account_types', data=data)


class Platform:
    def __init__(self, platform_id, name):
        self.id = platform_id
        self.name = name

    def remove(self):
        sql.delete(table='account_types', where=f'platform={self.id}')
        sql.delete(table='platforms', where=f'id={self.id}')


class Account:
    def __init__(self, account_id, platform_id, name, price, min_price, description):
        self.id = account_id
        self.platform_id = platform_id
        self.name = name
        self.price = price
        self.min_price = min_price
        self.description = description

    def update_name(self, name):
        sql.update(table='account_types', values={'name': name}, where=f'id={self.id}')

    def update_price(self, price):
        sql.update(table='account_types', values={'price': price}, where=f'id={self.id}')

    def update_min_price(self, min_price):
        sql.update(table='account_types', values={'min_price': min_price}, where=f'id={self.id}')

    def update_description(self, description):
        sql.update(table='account_types', values={'description': description}, where=f'id={self.id}')

    def remove(self):
        sql.delete(table='account_types', where=f'id={self.id}')

