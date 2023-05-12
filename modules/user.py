from copy import copy
from modules.sql import MysqlCollector
from configparser import ConfigParser
from json import dumps, loads

config = ConfigParser()
config.read('config.ini')

sql = MysqlCollector(**config['sql'])


def select(**kwargs):
    sql_copy = copy(sql)
    result = sql_copy.select(**kwargs)
    del sql_copy
    return result


class User:
    def __init__(self, user_id):
        self.id = user_id

        data = select(table='users', where=f'id={self.id}')['data']

        if not data:
            user_data = {'id': self.id, 'status': 'menu', 'data': '{}', 'messages': '[]'}
            sql.insert(table='users', data=user_data)

            self.status = 'menu'
            self.data = {}
            self.messages = []
            self.is_admin = bool(select(table='admins', where=f'id={self.id}')['data'])
        else:
            self.status = data['status']
            self.data = loads(data['data'])
            self.messages: list[int] = loads(data['messages'])
            self.is_admin = bool(select(table='admins', where=f'id={self.id}')['data'])

    def update_status(self, status):
        sql.update(table='users', values={'status': status}, where=f'id={self.id}')
        self.status = status

    def update_data(self, data):
        if 'description' in data and data['description']:
            data['description'] = data['description'].replace('\n', '\\n')
        sql.update(table='users', values={'data': dumps(data, ensure_ascii=False)}, where=f'id={self.id}')
        self.data = data

    def switch_admin(self, name='Администратор*'):
        if self.is_admin:
            sql.delete(table='admins', where=f'id={self.id}')
        else:
            sql.insert(table='admins', data={'id': self.id, 'name': name})

    def add_message(self, message_id):
        self.messages.append(message_id)
        sql.update(table='users', values={'messages': dumps(self.messages)}, where=f'id={self.id}')

    def remove_message(self, message_id):
        if message_id in self.messages:
            self.messages.remove(message_id)
            sql.update(table='users', values={'messages': dumps(self.messages)}, where=f'id={self.id}')

    def clean_messages(self):
        self.messages = []
        sql.update(table='users', values={'messages': dumps(self.messages)}, where=f'id={self.id}')