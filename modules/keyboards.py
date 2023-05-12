from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from configparser import ConfigParser
from modules.kyc import Platform, Account
from modules.admin import Admin


class Keyboards:
    def __init__(self):
        self.menu_admins = InlineKeyboardMarkup()
        self.menu_admins.add(InlineKeyboardButton(text='Управление админами', callback_data='admin_editor'))
        self.menu_admins.add(InlineKeyboardButton(text='Управление KYCами', callback_data='kyc_list'))
        self.menu_admins.add(InlineKeyboardButton(text='Редактировать "FAQ"', callback_data='edit_faq'))
        self.menu_admins.add(InlineKeyboardButton(text='Изменить ссылку сапорта', callback_data='edit_support'))

        self.cancel = ReplyKeyboardMarkup(resize_keyboard=True)
        self.cancel.add(KeyboardButton(text='Отмена ❌'))

        self.currency = InlineKeyboardMarkup()
        self.currency.add(InlineKeyboardButton(text='USDT (TRC20, BEP20, ERC20)', callback_data='usdt'))
        self.currency.add(InlineKeyboardButton(text='USDC (TRC20, BEP20, ERC20)', callback_data='usdc'))
        self.currency.add(InlineKeyboardButton(text='BUSD (BEP20, ERC20)', callback_data='busd'))
        self.currency.add(InlineKeyboardButton(text='Отменить заказ ❌', callback_data='cancel_order'))

        self.back_to_platforms = InlineKeyboardMarkup()
        self.back_to_platforms.add(InlineKeyboardButton(text='Назад ↩️', callback_data=f'kyc_list'))

        self.usdt_networks = InlineKeyboardMarkup()
        self.usdt_networks.add(InlineKeyboardButton(text='TRC20', callback_data='usdt_trc20'))
        self.usdt_networks.add(InlineKeyboardButton(text='BEP20', callback_data='usdt_bep20'))
        self.usdt_networks.add(InlineKeyboardButton(text='ERC20', callback_data='usdt_erc20'))
        self.usdt_networks.add(InlineKeyboardButton(text='Изменить валюту ↩️', callback_data='back'))

        self.usdc_networks = InlineKeyboardMarkup()
        self.usdc_networks.add(InlineKeyboardButton(text='TRC20', callback_data='usdc_trc20'))
        self.usdc_networks.add(InlineKeyboardButton(text='BEP20', callback_data='usdc_bep20'))
        self.usdc_networks.add(InlineKeyboardButton(text='ERC20', callback_data='usdc_erc20'))
        self.usdc_networks.add(InlineKeyboardButton(text='Изменить валюту ↩️', callback_data='back'))

        self.busd_networks = InlineKeyboardMarkup()
        self.busd_networks.add(InlineKeyboardButton(text='BEP20', callback_data='busd_bep20'))
        self.busd_networks.add(InlineKeyboardButton(text='ERC20', callback_data='busd_erc20'))
        self.busd_networks.add(InlineKeyboardButton(text='Изменить валюту ↩️', callback_data='back'))

        self.confirm_order = InlineKeyboardMarkup()
        self.confirm_order.add(InlineKeyboardButton(text='Отменить заказ ❌', callback_data='cancel'),
                               InlineKeyboardButton(text='Всё верно ✅', callback_data='confirm'))

        self.confirm_username = InlineKeyboardMarkup()
        self.confirm_username.add(InlineKeyboardButton(text='Понятно', callback_data='confirm_username'))

        self.check_order = InlineKeyboardMarkup()
        self.check_order.add(InlineKeyboardButton(text='Проверить поступление 🔁', callback_data='check'))
        self.check_order.add(InlineKeyboardButton(text='Отменить заказ ❌', callback_data='cancel_order'))

        self.cancel_order = InlineKeyboardMarkup()
        self.cancel_order.add(InlineKeyboardButton(text='Отменить заказ ❌', callback_data='cancel'))
        self.cancel_order.add(InlineKeyboardButton(text='Вернуться к оплате ↩️', callback_data='back'))

        self.back_to_menu = InlineKeyboardMarkup()
        self.back_to_menu.add(InlineKeyboardButton(text='Вернуться в меню ↩️', callback_data='menu'))

        self.admin_editor = InlineKeyboardMarkup()
        self.admin_editor.add(InlineKeyboardButton(text='Список администраторов', callback_data='admin_list'))
        self.admin_editor.add(InlineKeyboardButton(text='Добавить администратора', callback_data='add_admin'))
        self.admin_editor.add(InlineKeyboardButton(text='Назад ↩️', callback_data='menu'))

        self.back_to_admin_editor = InlineKeyboardMarkup()
        self.back_to_admin_editor.add(InlineKeyboardButton(text='Назад ↩️', callback_data='admin_editor'))

        self.account_creator = InlineKeyboardMarkup()
        self.account_creator.add(InlineKeyboardButton(text='Имя', callback_data=f'name'),
                                 InlineKeyboardButton(text='Описание', callback_data=f'description'))
        self.account_creator.add(InlineKeyboardButton(text='Стоимость', callback_data=f'price'),
                                 InlineKeyboardButton(text='Мин. цена', callback_data=f'min_price'))
        self.account_creator.add(InlineKeyboardButton(text='Создать ➕', callback_data=f'create'))
        self.account_creator.add(InlineKeyboardButton(text='Отмена ❌', callback_data=f'cancel'))

        self.back_to_creator = InlineKeyboardMarkup()
        self.back_to_creator.add(InlineKeyboardButton(text='Назад ↩️', callback_data='back'))

    def back_to_platform(self, platform: Platform):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Назад ↩️', callback_data=f'platform_{platform.id}'))
        return keyboard

    def confirm_admin_delete(self, admin_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Да', callback_data=f'delete_admin_{admin_id}'),
                     InlineKeyboardButton(text='Нет', callback_data=f'admin_list'))
        return keyboard

    def generate_admin_list(self, admins: list[Admin]):
        keyboard = InlineKeyboardMarkup()
        for i in admins:
            keyboard.add(InlineKeyboardButton(text=i.name, callback_data=f'delete_ask_{i.id}'))
        keyboard.add(InlineKeyboardButton(text='Назад ↩️', callback_data='admin_editor'))
        return keyboard

    def menu_users(self, url):
        menu_users = InlineKeyboardMarkup()
        menu_users.add(InlineKeyboardButton(text='FAQ ℹ️', callback_data='show_faq'))
        menu_users.add(InlineKeyboardButton(text='KYCы 🌍', callback_data='kyc_list'))
        menu_users.add(InlineKeyboardButton(text='Support 👤', url=url))
        return menu_users

    def generate_platforms_keyboard(self, platforms: list[Platform], for_admins=False):
        keyboard = InlineKeyboardMarkup()
        for i in platforms:
            keyboard.add(InlineKeyboardButton(text=i.name, callback_data=f'platform_{i.id}'))
        if for_admins:
            keyboard.add(InlineKeyboardButton(text='Создать платформу ➕', callback_data='create_platform'))
        keyboard.add(InlineKeyboardButton(text='Вернуться в меню ↩️', callback_data='menu'))
        return keyboard

    def generate_accounts_keyboard(self, accounts: list[Account], platform_id=None):
        keyboard = InlineKeyboardMarkup()
        for i in accounts:
            keyboard.add(InlineKeyboardButton(text=i.name, callback_data=f'account_{i.id}'))
        if platform_id:
            keyboard.add(InlineKeyboardButton(text='Удалить платформу ❌', callback_data=f'delete_platform_{platform_id}'),
                         InlineKeyboardButton(text='Создать аккаунт ➕', callback_data=f'create_account_{platform_id}'))
        keyboard.add(InlineKeyboardButton(text='Назад к платформам ↩️', callback_data='kyc_list'))
        return keyboard

    def generate_account_keyboard(self, account):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Перейти к заказу', callback_data=f'order_{account.id}'))
        keyboard.add(InlineKeyboardButton(text='Назад ↩️', callback_data=f'platform_{account.platform_id}'))
        return keyboard

    def generate_back_to_account_button(self, account: Account = None, account_id = None):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Назад ↩️', callback_data=f'account_{account.id if account else account_id}'))
        return keyboard

    def generate_kyc_editor(self, account: Account = None, account_id = None):
        if not account_id:
            account_id = account.id
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Имя', callback_data=f'edit_account_name_{account_id}'),
                     InlineKeyboardButton(text='Описание', callback_data=f'edit_description_{account_id}'))
        keyboard.add(InlineKeyboardButton(text='Стоимость', callback_data=f'edit_price_{account_id}'),
                     InlineKeyboardButton(text='Мин. цена', callback_data=f'edit_min_price_{account_id}'))
        keyboard.add(InlineKeyboardButton(text='Удалить ❌', callback_data=f'delete_account_{account_id}'))
        keyboard.add(InlineKeyboardButton(text='Назад ↩️', callback_data=f'platform_{account.platform_id}'))

        return keyboard

    def generate_delete_account(self, account: Account):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Да', callback_data=f'delete_account_confirm_{account.id}'),
                     InlineKeyboardButton(text='Нет', callback_data=f'account_{account.id}'))
        return keyboard

    def generate_delete_platform(self, platform: Platform):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Да', callback_data=f'delete_platform_confirm_{platform.id}'),
                     InlineKeyboardButton(text='Нет', callback_data=f'platform_{platform.id}'))
        return keyboard
