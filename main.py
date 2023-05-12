import telebot
from configparser import ConfigParser
from modules.user import User
from modules.bot import Bot
from re import fullmatch

telebot.apihelper.ENABLE_MIDDLEWARE = True

config = ConfigParser()
config.read('config.ini')

api = telebot.TeleBot(token=config['telegram']['token'], parse_mode='HTML')
bot = Bot(api)


@api.middleware_handler()
def middleware(bot_instance, upd):
    if upd.message:
        uid = upd.message.chat.id
    elif upd.callback_query:
        uid = upd.callback_query.message.chat.id
    else:
        uid = 0

    if uid:
        user = User(uid)

        if upd.message:
            upd.message.user_data = user
        else:
            upd.callback_query.user_data = user


@api.message_handler(commands=['start'])
def start(message):
    user = message.user_data
    bot.reload_user(user)
    bot.remove_keyboard(user)
    bot.delete_old_messages(user)
    bot.send_menu(user)


@api.callback_query_handler(func=lambda call: not call.user_data.is_admin)
def callback_users(call: telebot.types.CallbackQuery):
    user = call.user_data
    data = call.data

    if user.status == 'menu':
        if data == 'menu':
            bot.edit_menu(user, call.message)

        elif data == 'kyc_list':
            bot.edit_platforms(user, call.message)

        elif data == 'show_faq':
            bot.edit_faq(user, call.message)

        elif fullmatch(r'platform_\d*', data):
            platform_id = fullmatch(r'platform_(\d*)', data).groups()[0]
            bot.edit_accounts(user, call.message, platform_id)

        elif fullmatch(r'account_\d*', data):
            account_id = fullmatch(r'account_(\d*)', data).groups()[0]
            bot.edit_account_type(user, call.message, account_id)

        elif fullmatch(r'order_\d*', data):
            account_id = fullmatch(r'order_(\d*)', data).groups()[0]
            bot.start_order(user, call.message, account_id, call.from_user.username)

    elif user.status == 'choose_currency':
        bot.get_order_currency(user, call.message, data)

    elif user.status == 'confirm':
        bot.confirm_order(user, call.message, data)

    elif user.status == 'paying':
        bot.payment(user, call, data, call.id)


@api.callback_query_handler(func=lambda call: call.user_data.is_admin)
def callback_admins(call):
    user = call.user_data
    data = call.data

    if user.status == 'menu':
        if data == 'menu':
            bot.edit_menu(user, call.message)
        elif data == 'edit_faq':
            bot.change_faq(user, call.message)
        elif data == 'edit_support':
            bot.change_support(user, call.message)
        elif data == 'admin_editor':
            bot.admin_editor(user, call.message)
        elif data == 'admin_list':
            bot.admin_list(user, call.message)
        elif fullmatch(r'delete_ask_\d*', data):
            admin_id = fullmatch(r'delete_ask_(\d*)', data).groups()[0]
            bot.delete_admin(user, call.message, admin_id)
        elif fullmatch(r'delete_admin_\d*', data):
            admin_id = fullmatch(r'delete_admin_(\d*)', data).groups()[0]
            bot.confirm_delete_admin(user, call.message, call.id, admin_id)
        elif data == 'add_admin':
            bot.create_admin(user, call.message)
        elif data == 'kyc_list':
            bot.kyc_editor_platforms(user, call.message)
        elif fullmatch(r'platform_\d*', data):
            platform_id = fullmatch(r'platform_(\d*)', data).groups()[0]
            bot.kyc_editor_accounts(user, call.message, platform_id)
        elif fullmatch(r'account_\d*', data):
            account_id = fullmatch(r'account_(\d*)', data).groups()[0]
            bot.kyc_editor_account(user, call.message, account_id)
        elif fullmatch(r'edit_account_name_\d*', data):
            account_id = fullmatch(r'edit_account_name_(\d*)', data).groups()[0]
            bot.start_account_name_editing(user, call.message, account_id)
        elif fullmatch(r'edit_description_\d*', data):
            account_id = fullmatch(r'edit_description_(\d*)', data).groups()[0]
            bot.start_account_description_editing(user, call.message, account_id)
        elif fullmatch(r'edit_price_\d*', data):
            account_id = fullmatch(r'edit_price_(\d*)', data).groups()[0]
            bot.start_account_price_editing(user, call.message, account_id)
        elif fullmatch(r'edit_min_price_\d*', data):
            account_id = fullmatch(r'edit_min_price_(\d*)', data).groups()[0]
            bot.start_account_min_price_editing(user, call.message, account_id)
        elif fullmatch(r'delete_account_confirm_\d*', data):
            account_id = fullmatch(r'delete_account_confirm_(\d*)', data).groups()[0]
            bot.delete_account_confirm(user, call.message, account_id)
        elif fullmatch(r'delete_account_\d*', data):
            account_id = fullmatch(r'delete_account_(\d*)', data).groups()[0]
            bot.delete_account(user, call.message, account_id)
        elif data == 'create_platform':
            bot.create_platform(user, call.message)
        elif fullmatch(r'delete_platform_\d*', data):
            platform_id = fullmatch(r'delete_platform_(\d*)', data).groups()[0]
            bot.delete_platform(user, call.message, platform_id)
        elif fullmatch(r'delete_platform_confirm_\d*', data):
            platform_id = fullmatch(r'delete_platform_confirm_(\d*)', data).groups()[0]
            bot.delete_platform_confirm(user, call.message, platform_id)
        elif fullmatch(r'create_account_\d*', data):
            platform_id = fullmatch(r'create_account_(\d*)', data).groups()[0]
            bot.create_account(user, call.message, platform_id)

    elif user.status == 'create_account':
        bot.account_creator(user, call.message, call.id, data)


@api.message_handler(func=lambda message: message.user_data.is_admin)
def text_admins(message):
    user = message.user_data

    if user.status == 'menu':
        bot.remove_keyboard(user)
        bot.delete_message(user, message)
    elif user.status == 'edit_faq':
        bot.get_new_faq(user, message)
    elif user.status == 'edit_support':
        bot.get_new_support(user, message)
    elif user.status == 'edit_account_name':
        bot.edit_account_name(user, message)
    elif user.status == 'edit_account_description':
        bot.edit_account_description(user, message)
    elif user.status == 'edit_account_price':
        bot.edit_account_price(user, message)
    elif user.status == 'edit_account_min_price':
        bot.edit_account_min_price(user, message)
    elif user.status == 'creating_admin':
        bot.get_new_admin_id(user, message)
    elif user.status == 'creating_admin_name':
        bot.get_new_admin_name(user, message)
    elif user.status == 'creating_platform':
        bot.get_new_platform_name(user, message)
    elif user.status == 'create_account_name':
        bot.get_new_account_name(user, message)
    elif user.status == 'create_account_description':
        bot.get_new_account_description(user, message)
    elif user.status == 'create_account_price':
        bot.get_new_account_price(user, message)
    elif user.status == 'create_account_min_price':
        bot.get_new_account_min_price(user, message)


@api.message_handler(func=lambda message: not message.user_data.is_admin)
def text_users(message):
    user = message.user_data

    if user.status == 'menu':
        bot.remove_keyboard(user)
        bot.delete_message(user, message)
    elif user.status == 'order_count':
        bot.get_order_amount(user, message)


if __name__ == '__main__':
    api.infinity_polling()