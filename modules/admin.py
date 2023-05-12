from copy import copy
from modules.sql import MysqlCollector
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

sql = MysqlCollector(**config['sql'])


def select(**kwargs):
    sql_copy = copy(sql)
    result = sql_copy.select(**kwargs)
    del sql_copy
    return result


def get_admin_list():
    data = select(table='admins')['data']

    if not isinstance(data, list):
        data = [data]

    admins = [Admin(i['id'], i['name']) for i in data]

    return admins


def create_admin(admin_id, name):
    sql.insert(table='admins', data={'id': admin_id, 'name': name})


def get_admin_by_id(user_id):
    data = select(table='admins', where=f'id={user_id}')['data']
    if not data:
        return None
    else:
        return Admin(data['id'], data['name'])


class Admin:
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name

    def remove(self):
        sql.delete(table='admins', where=f'id={self.id}')