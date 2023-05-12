from telebot.apihelper import ApiTelegramException
from modules.user import User
from telebot.types import ReplyKeyboardRemove, InlineKeyboardMarkup, Message
from telebot import TeleBot
from modules.keyboards import Keyboards
import modules.kyc as kyc
from re import fullmatch
from modules.wallets import Erc, Trc, Bsc
from configparser import ConfigParser
from modules.sheets import Sheet
from requests import get
import modules.admin as admin

config = ConfigParser()
config.read('config.ini')

tron = Trc()
erc = Erc(config['blockchain']['erc'])
bsc = Bsc(config['blockchain']['bsc'])


class WalletBot:
    def __init__(self):
        self.bot = TeleBot(token=config['telegram']['wallets_token'], parse_mode='HTML')

    def send_wallet(self, network, currency, private, address, amount):
        text = '<b>Создан новый кошелёк</b>\n\n' \
               f'<b>Адрес:</b> {address}\n\n' \
               f'<b>Сеть:</b> {network}\n' \
               f'<b>Монета:</b> {currency.upper()}\n' \
               f'<b>Ожидается:</b> {amount:.2f} {currency.upper()}\n\n' \
               f'<b>Данные для входа</b>: <code>{private}</code>'

        self.bot.send_message(chat_id=int(config['telegram']['wallets_allowed']), text=text)


class Bot:
    def __init__(self, bot: TeleBot):
        self.bot: TeleBot = bot
        self.keyboards = Keyboards()
        self.wallets = WalletBot()

        self.busy = False

    # Перезапуск бота у пользователя. Убирает клавиатуры, меняет статус и данные в БД на стандартные
    def reload_user(self, user: User):
        user.update_data({})
        user.update_status('menu')

    # Отменяет действие, связанное с отправкой боту текстового сообщения
    def cancel_action(self, user):
        self.reload_user(user)
        self.remove_keyboard(user)
        text = 'Отменено'
        keyboard = self.keyboards.back_to_menu
        self.send_message(user, text=text, reply_markup=keyboard)

    # Отправляет пользователю сообщение с пустой клавиатурой, а затем удаляет его
    def remove_keyboard(self, user: User):
        m = self.send_message(user=user, text='!', reply_markup=ReplyKeyboardRemove())
        self.delete_message(user, m)

    # Удаляет ненужные сообщения с inline-клавиатурой
    def delete_old_messages(self, user: User):
        for message in user.messages:
            self.delete_message(user, chat_id=user.id, message_id=message)
        user.clean_messages()

    # Удаляет сообщение, если это возможно. Если нет - заменяет его текст на "Сообщение устарело"
    def delete_message(self, user: User, message: Message = None, chat_id=None, message_id=None):
        if not message and not (chat_id or message_id):
            return

        if message:
            chat_id = message.chat.id,
            message_id = message.id

        if message_id in user.messages:
            user.remove_message(message_id)

        try:
            self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except ApiTelegramException as e:
            if e.result_json['description'] in ("Bad Request: message can't be deleted for everyone", "Bad Request: message can't be edited"):
                if message.content_type == 'text':
                    self.bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text='Сообщение устарело')
                else:
                    self.bot.edit_message_caption(chat_id=message.chat.id, message_id=message.id, caption='Сообщение устарело')

    # Отправляет сообщение и, если в нём есть inline-клавиатура, сохраняет его id в БД
    def send_message(self, user: User, **kwargs):
        m = self.bot.send_message(chat_id=user.id, **kwargs)
        if isinstance(kwargs.get('reply_markup'), InlineKeyboardMarkup):
            user.add_message(m.id)
        return m

    # Отменяет заказ пользователя. Ставит стандартный статус и данные в БД, изменяет сообщение и клавиатуру
    def cancel_order(self, user, message: Message):
        account_id = user.data['account_id']
        self.reload_user(user)
        text = 'Оформление заказа отменено'
        keyboard = self.keyboards.generate_back_to_account_button(account_id=account_id)
        if message.from_user.is_bot:
            self.edit_message(user, message, text=text, reply_markup=keyboard)
        else:
            self.remove_keyboard(user)
            self.send_message(user, text=text, reply_markup=keyboard)

    # Редактирует сообщение, если это возможно. Если нет - удаляет и присылает вместо него новое
    def edit_message(self, user: User, message: Message, **kwargs):
        if message.content_type == 'text':
            self.bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, **kwargs)
        else:
            user.remove_message(message.id)
            self.send_message(user, **kwargs)

    # Отправляет пользователю главное меню
    def send_menu(self, user: User):
        admin = user.is_admin
        if not admin:
            text = '<b>🏠 Главное меню 🏠</b>\n\n' \
                   '' \
                   'Добро пожаловать! Здесь Вы сможете найти, выбрать и заказать KYCы отличного качества :)'
        else:
            text = '<b>Панель администратора</b>'
        keyboard = self.keyboards.menu_users(config['telegram']['support_url']) if not admin else self.keyboards.menu_admins
        self.send_message(user, text=text, reply_markup=keyboard)

    # Редактирует текущее сообщение на сообщение с меню
    def edit_menu(self, user: User, message: Message):
        admin = user.is_admin
        if not admin:
            text = '<b>🏠 Главное меню 🏠</b>\n\n' \
                   '' \
                   'Добро пожаловать! Здесь Вы сможете найти, выбрать и заказать KYCы отличного качества :)'
        else:
            text = '<b>Панель администратора</b>'
        keyboard = self.keyboards.menu_users(config['telegram']['support_url']) if not admin else self.keyboards.menu_admins

        if message.content_type == 'text':
            self.bot.edit_message_text(chat_id=user.id, message_id=message.id, text=text, reply_markup=keyboard)
        else:
            self.delete_message(user, message)
            self.send_message(user, text=text, reply_markup=keyboard)

    # Открывает раздел FAQ
    def edit_faq(self, user: User, message: Message):
        with open('faq.txt', encoding='utf-8') as file:
            text = file.read()
            keyboard = self.keyboards.back_to_menu
            self.edit_message(user, message, text=text, reply_markup=keyboard, disable_web_page_preview=True)

    # Редактирует текущее сообщение на список доступных платформ
    def edit_platforms(self, user: User, message):
        platforms = kyc.get_platform_list()
        keyboard = self.keyboards.generate_platforms_keyboard(platforms)

        text = '<b>🌐 Доступные платформы 🌐</b>\n\n' \
               '' \
               'Здесь все доступные для заказа на данный момент платформы\n\n' \
               '' \
               'Выберите платформу из списка'
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Редактирует текущее сообщение на список видов аккаунтов, доступных для platform_id
    def edit_accounts(self, user: User, message, platform_id):
        platform = kyc.get_platform_by_id(platform_id)

        if not platform:
            keyboard = self.keyboards.back_to_platforms
            text = f'Выбранной платформы больше нет в списке'
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        accounts = kyc.get_accounts_by_platform_id(platform_id)
        keyboard = self.keyboards.generate_accounts_keyboard(accounts)

        text = f'<b>👤 Виды аккаунтов 👤</b>\n\n' \
               f'' \
               f'Здесь Вы можете выбрать вид аккаунта для платформы <b>{platform.name}</b>\n\n' \
               f'' \
               f'Выберите вид аккаунта из списка'
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Редактирует текущее сообщение на карточку выбранного товара account_id
    def edit_account_type(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            keyboard = self.keyboards.back_to_platforms
            text = f'Данного типа аккаунтов больше нет в списке'
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        platform = kyc.get_platform_by_id(platform_id=account.platform_id)
        keyboard = self.keyboards.generate_account_keyboard(account)

        text = f'<b>Карточка товара</b>\n\n' \
               f'' \
               f'<b>🌐 Платформа:</b> {platform.name}\n' \
               f'<b>👤 Вид аккаунта:</b> {account.name}\n\n' \
               f'' \
               f'<b>💰 Стоимость:</b> {account.price:.2f}$\n'
        if account.min_price:
            text += f'<b>🔥 Мин. заказ:</b> {account.min_price:.2f}$\n'

        text += f'\n{account.description}'

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Нужен для обработки нажатия кнопки "Перейти к заказу", готовит пользователя в БД для заказа
    def start_order(self, user, message, account_id, username):
        account = kyc.get_account_by_id(account_id)

        if not account:
            keyboard = self.keyboards.back_to_platforms
            text = f'Данного типа аккаунтов больше нет в списке'
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        if not username:
            text = '<b>❗Внимание❗</b>\n\n' \
                   'Для совершения заказа нужно установить <b>username</b>. Это необходимо для того, чтобы мы смогли с Вами связаться для уточнения деталей заказа.\n\n' \
                   'После совершения заказа и до его завершения <b>НЕЛЬЗЯ</b> менять username, так как в этом случае мы не сможем Вас найти.\n\n' \
                   '<b>Устанавливается username следующим образом:</b>\n' \
                   'Настройки -> Изменить профиль -> Имя пользователя'
            keyboard = self.keyboards.generate_back_to_account_button(account=account)
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        platform = kyc.get_platform_by_id(account.platform_id)

        data = {
            'account_id': account_id,
            'amount': None,
            'order': {
                'platform': platform.name,
                'account': account.name
            },
            'payment': {
                'network': None,
                'currency': None,
                'wallet': None,
                'value': None
            }
        }

        self.delete_message(user, message)

        user.update_status('order_count')
        user.update_data(data)

        text = f'Вы собираетесь заказать <b>[{platform.name} | {account.name}]</b>\n\n' \
               f'Стоимость - <b>${account.price:.2f} за штуку</b>\n\n' \
               f'Отправьте в чат количество товара, которое Вы хотите заказать.'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    # Обрабатываем количество товара, введённое пользователем
    def get_order_amount(self, user, message):
        if message.text == 'Отмена ❌':
            self.cancel_order(user, message)
            return

        try:
            amount = abs(int(message.text))
        except ValueError:
            text = 'Для записи количество используются только целые числа'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
        else:
            if not amount:
                text = 'Количество единиц заказа не может быть нулевым'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

            account = kyc.get_account_by_id(user.data['account_id'])

            if not account:
                self.reload_user(user)
                self.remove_keyboard(user)
                keyboard = self.keyboards.back_to_platforms
                text = 'Товар, который вы собирались заказать, был удалён'
                self.send_message(user, text=text, reply_markup=keyboard)
                return

            platform = kyc.get_platform_by_id(account.platform_id)

            if account.min_price > amount * account.price:
                text = f'На пакет установлена минимальная сумма покупки: <b>${account.min_price:.2f}</b>.\n\n' \
                       f'<b>{amount}</b> единиц пакета будут стоить <b>${account.price * amount:.2f}</b>, что меньше минимальной суммы.'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

            user.data['amount'] = amount
            user.data['payment']['value'] = round(amount * account.price, 2)
            user.update_data(user.data)

            user.update_status('choose_currency')
            self.remove_keyboard(user)

            text = f'Вы собираетесь заказать <b>{amount}</b> единиц <b>[{platform.name} | {account.name}]</b>\n\n' \
                   f'Итоговая сумма: <b>${account.price * amount:.2f}</b>\n\n' \
                   f'<b>Выберите валюту, в которой будет оплачен заказ</b>'
            keyboard = self.keyboards.currency
            self.send_message(user, text=text, reply_markup=keyboard)

    # Обрабатываем валюту и сеть, выбранную пользователем
    def get_order_currency(self, user, message, cdata):
        if cdata == 'cancel_order':
            self.cancel_order(user, message)
            return

        if cdata == 'back':
            amount = user.data['amount']
            account = kyc.get_account_by_id(user.data['account_id'])
            if not account:
                self.reload_user(user)
                text = 'Товар, с которым вы работали, был удалён'
                keyboard = self.keyboards.back_to_platforms
                self.edit_message(user, message, text=text, reply_markup=keyboard)
                return
            platform = kyc.get_platform_by_id(account.platform_id)

            text = f'Вы собираетесь заказать <b>{amount}</b> единиц <b>[{platform.name} | {account.name}]</b>\n\n' \
                   f'Итоговая сумма: <b>${account.price * amount:.2f}</b>\n\n' \
                   f'<b>Выберите валюту, в которой будет оплачен заказ</b>'
            keyboard = self.keyboards.currency

            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        if cdata in ('usdt', 'usdc', 'busd'):
            if cdata == 'usdt':
                text = 'Выберите сеть для оплаты в <b>USDT</b>'
                keyboard = self.keyboards.usdt_networks
            elif cdata == 'usdc':
                text = 'Выберите сеть для оплаты в <b>USDC</b>'
                keyboard = self.keyboards.usdc_networks
            else:
                text = 'Выберите сеть для оплаты в <b>BUSD</b>'
                keyboard = self.keyboards.busd_networks

            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        if fullmatch(r'(usdt|usdc|busd)_(erc20|trc20|bep20)', cdata):
            currency, network = fullmatch(r'(usdt|usdc|busd)_(erc20|trc20|bep20)', cdata).groups()

            user.data['payment']['network'] = network
            user.data['payment']['currency'] = currency

            user.update_data(user.data)
            user.update_status('confirm')

            account = kyc.get_account_by_id(user.data['account_id'])

            if not account:
                if not account:
                    self.reload_user(user)
                    text = 'Товар, с которым вы работали, был удалён'
                    keyboard = self.keyboards.back_to_platforms
                    self.edit_message(user, message, text=text, reply_markup=keyboard)
                    return

            platform = kyc.get_platform_by_id(account.platform_id)

            price = round(account.price * user.data['amount'], 2)

            text = f'<b>⚠️ Подтверждение заказа ⚠️</b>\n\n' \
                   f'<b>Платформа:</b> {platform.name}\n\n' \
                   f'<b>Вид аккаунта:</b> {account.name}\n\n' \
                   f'<b>Цена за единицу:</b> ${account.price:.2f}\n\n' \
                   f'<b>Количество:</b> {user.data["amount"]}\n\n' \
                   f'<b>Итоговая стоимость:</b> ${price:.2f}\n\n' \
                   f'<b>Валюта оплаты:</b> {user.data["payment"]["currency"].upper()}\n\n' \
                   f'<b>Сеть для оплаты:</b> {user.data["payment"]["network"].upper()}\n\n' \
                   f'<b>⚠️ Внимательно проверьте все пункты и подтвердите или отмените заказ ⚠️</b>'
            keyboard = self.keyboards.confirm_order

            self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Обрабатываем этап подтверждения заказа
    def confirm_order(self, user: User, message: Message, cdata):
        if cdata == 'cancel':
            self.cancel_order(user, message)
            return

        if cdata == 'confirm':
            if not message.from_user.username:
                text = '<b>❗Внимание❗</b>\n\n' \
                       'Для совершения заказа нужно установить <b>username</b>. Это необходимо для того, чтобы мы смогли с Вами связаться для уточнения деталей заказа.\n\n' \
                       'После совершения заказа и до его завершения <b>НЕЛЬЗЯ</b> менять username, так как в этом случае мы не сможем Вас найти.\n\n' \
                       '<b>Устанавливается username следующим образом:</b>\n' \
                       'Настройки -> Изменить профиль -> Имя пользователя'
                keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
                self.reload_user(user)
                self.edit_message(user, message, text=text, reply_markup=keyboard)
                return

            text = '<b>❗Внимание❗</b>\n\n' \
                   'После оплаты заказа и до его завершения <b>НЕЛЬЗЯ</b> менять свой username.\n\n' \
                   'Если сделать это, мы не сможем с Вами связаться для уточнения деталей заказа и других нюансов.'
            keyboard = self.keyboards.confirm_username

            self.edit_message(user, message, text=text, reply_markup=keyboard)

        elif cdata == 'confirm_username':
            account = kyc.get_account_by_id(user.data['account_id'])

            if not account:
                self.reload_user(user)
                text = 'Товар, который Вы пытались заказать, был удалён.'
                keyboard = self.keyboards.back_to_platforms
                self.edit_message(user, message, text=text, reply_markup=keyboard)
                return

            user.update_status('paying')
            currency = user.data['payment']['currency']
            network = user.data['payment']['network']

            if network == 'trc20':
                address, phrase = tron.create_wallet()
            elif network == 'erc20':
                address, phrase = erc.create_wallet()
            else:
                address, phrase = bsc.create_wallet()

            user.data['payment']['wallet'] = address
            user.update_data(user.data)

            value = account.price * user.data['amount']
            self.wallets.send_wallet(user.data['payment']['network'], user.data['payment']['currency'], phrase, address, value)

            text = f'Используйте данные ниже для оплаты заказа:\n\n' \
                   f'Валюта: <b>{currency.upper()}</b>\n' \
                   f'Сеть: <b>{network.upper()}</b>\n' \
                   f'Cумма: <b>{value} {currency.upper()}</b>\n\n' \
                   f'<code>{address}</code>\n\n' \
                   f'⚠️ <i>Отправляйте только <b>{currency.upper()}</b> через сеть <b>{network.upper()}</b>, иначе монеты будут утеряны</i>'
            keyboard = self.keyboards.check_order

            self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Обрабатывает оплату заказа
    def payment(self, user: User, call, cdata, call_id):
        message = call.message
        if cdata == 'cancel_order':
            text = 'Вы уверены, что хотите отменить заказ?\n\n' \
                   'Если отменить заказ, к нему невозможно будет вернуться, даже если токены уже отправлены.'
            keyboard = self.keyboards.cancel_order
            self.edit_message(user, message, text=text, reply_markup=keyboard)
        elif cdata == 'cancel':
            text = 'Заказ отменён'
            keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
            self.reload_user(user)
            self.edit_message(user, message, text=text, reply_markup=keyboard)
        elif cdata == 'back':
            currency = user.data['payment']['currency']
            network = user.data['payment']['network']
            address = user.data['payment']['wallet']
            value = user.data['payment']['value']

            text = f'Используйте данные ниже для оплаты заказа:\n\n' \
                   f'Валюта: <b>{currency.upper()}</b>\n' \
                   f'Сеть: <b>{network.upper()}</b>\n' \
                   f'Cумма: <b>{value} {currency.upper()}</b>\n\n' \
                   f'<code>{address}</code>\n\n' \
                   f'⚠️ <i>Отправляйте только <b>{currency.upper()}</b> через сеть <b>{network.upper()}</b>, иначе монеты будут утеряны</i>'
            keyboard = self.keyboards.check_order

            self.edit_message(user, message, text=text, reply_markup=keyboard)
        elif cdata == 'check':
            currency = user.data['payment']['currency']
            network = user.data['payment']['network']
            address = user.data['payment']['wallet']
            value = user.data['payment']['value']

            if network == 'erc20':
                if currency == 'usdt':
                    contract = erc.usdt
                elif currency == 'usdc':
                    contract = erc.usdc
                else:
                    contract = erc.busd
                status = erc.get_transaction(value, contract, address)
            elif network == 'trc20':
                if currency == 'usdt':
                    contract = tron.usdt
                else:
                    contract = tron.usdc
                status = tron.get_transaction(value, contract, address)
            else:
                if currency == 'usdt':
                    contract = bsc.usdt
                elif currency == 'usdc':
                    contract = bsc.usdc
                else:
                    contract = bsc.busd
                status = bsc.get_transaction(value, contract, address)

            if status is None:
                self.bot.answer_callback_query(callback_query_id=call_id,
                                               text='Произошла ошибка. Попробуйте повторить попытку позже.')
            elif status is False:
                self.bot.answer_callback_query(callback_query_id=call_id,
                                               text='Транзакция не найдена, повторите попытку позже.',
                                               show_alert=True)
            else:
                udata_copy = user.data
                self.reload_user(user)

                text = '✔️ <b>Заказ успешно оплачен</b> ✔️\n\n' \
                       'Поздравляем! Ваш заказ успешно оплачен. Через некоторое время мы с Вами свяжемся, чтобы уточнить все детали.\n\n' \
                       'Мы выражаем Вам глубочайшую благодарность за покупку. Мы всегда стремимся предоставлять своим клиентам только высококачественные услуги.\n\n' \
                       '⚠️ <i>Пожалуйста, не меняйте свой username до завершения заказа. Если Вы это сделаете, мы не сможем с Вами связаться для уточнения деталей и передачи заказа.</i>'

                keyboard = self.keyboards.back_to_menu

                self.edit_message(user, message, text=text, reply_markup=keyboard)

                sheets = Sheet(key=config['sheets']['key'], token='key.json')

                while 1:
                    if not self.busy:
                        self.busy = True
                        order = {
                            'username': call.from_user.username,
                            'platform': udata_copy['order']['platform'],
                            'account': udata_copy['order']['account'],
                            'value': udata_copy['payment']['value'],
                            'amount': udata_copy['amount']
                        }
                        sheets.insert_order(**order)
                        self.busy = False
                        break

    # Изменяет статус пользователя, отправляет сообщение с просьбой прислать новый текст FAQ
    def change_faq(self, user: User, message: Message):
        user.update_status('edit_faq')
        text = 'Отправьте сообщение, содержащее новый текст раздела FAQ.\n\nЛюбое форматирование, кроме картинок,' \
               ' поддерживается.'
        keyboard = self.keyboards.cancel
        self.delete_message(user, message)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает новый текст FAQ и изменяет его в документе
    def get_new_faq(self, user: User, message: Message):
        if message.text == 'Отмена ❌':
            self.cancel_action(user)
            return

        new_text = message.html_text
        with open('faq.txt', 'w', encoding='utf-8') as file:
            file.write(new_text)
            file.close()

        text = 'Новый текст FAQ установлен ✅'
        keyboard = self.keyboards.back_to_menu

        user.update_status('menu')
        self.remove_keyboard(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Изменяет статус пользователя, отправляет сообщение с просьбой прислать новую ссылку на саппорта
    def change_support(self, user: User, message: Message):
        user.update_status('edit_support')
        text = 'Отправьте новую ссылку, которая будет открываться при нажатии на кнопку <b>Support</b>'
        keyboard = self.keyboards.cancel
        self.delete_message(user, message)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает и проверяет новую ссылку саппорта
    def get_new_support(self, user: User, message: Message):
        if message.text == 'Отмена ❌':
            self.cancel_action(user)
            return

        url = message.text
        try:
            get(url)
        except Exception:
            text = 'То, что Вы отправили, не является ссылкой, или эта ссылка недоступна'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        config['telegram']['support_url'] = url
        with open('config.ini', 'w', encoding='utf-8') as file:
            config.write(file)

        text = 'Новый ссылка для саппорта установлена ✅'
        keyboard = self.keyboards.back_to_menu

        user.update_status('menu')
        self.remove_keyboard(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Открывает раздел управления администраторами
    def admin_editor(self, user, message):
        text = '<b>Управление администраторами</b>\n\nВыберите пункт на клавиатуре'
        keyboard = self.keyboards.admin_editor
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Открывает список администраторов
    def admin_list(self, user, message):
        text = '<b>Список администраторов</b>\n\nНажмите на администратора, чтобы удалить его.'
        admin_list = admin.get_admin_list()
        keyboard = self.keyboards.generate_admin_list(admin_list)
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Предлагает удостовериться, что этого администратора нужно удалить
    def delete_admin(self, user, message, admin_id):
        adm = admin.get_admin_by_id(admin_id)
        text = f'Вы уверены, что хотите удалить администратора {adm.name}?'
        keyboard = self.keyboards.confirm_admin_delete(admin_id)
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Подтверждает удаление администратора
    def confirm_delete_admin(self, user, message, call_id, admin_id):
        admin_user = User(admin_id)
        admin_user.switch_admin()
        self.bot.answer_callback_query(callback_query_id=call_id, text=f'Администратор удалён')
        self.admin_list(user, message)

    def create_admin(self, user, message):
        user.update_status('creating_admin')
        user.update_data({'admin_id': None})
        text = 'Пришлите в чат id будущего администратора\n\n' \
               '' \
               'Узнать id пользователя можно с помощью бота @username_to_id_bot'
        keyboard = self.keyboards.cancel
        self.delete_message(user, message)
        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_admin_id(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_admin_editor
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        try:
            int(message.text)
        except ValueError:
            text = 'id нового администратора должен быть целым числом'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        user.data['admin_id'] = int(message.text)
        user.update_data(user.data)

        user.update_status(status='creating_admin_name')
        text = f'Введите имя для администратора <code>{int(message.text)}</code>'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_admin_name(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_admin_editor
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        name = message.text.replace('\n', ' ')
        admin_id = user.data['admin_id']
        self.reload_user(user)
        admin.create_admin(admin_id, name)

        self.remove_keyboard(user)
        text = f'Администратор <b>{name}</b> с id <b>{admin_id}</b> успешно создан!'
        keyboard = self.keyboards.back_to_admin_editor
        self.send_message(user, text=text, reply_markup=keyboard)

    # Открывает список платформ для админа
    def kyc_editor_platforms(self, user, message):
        platforms = kyc.get_platform_list()

        text = '<b>Редактирование KYC</b>'
        keyboard = self.keyboards.generate_platforms_keyboard(platforms, 1)

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Открывает список аккаунтов по id платформы для админа
    def kyc_editor_accounts(self, user, message, platform_id):
        platform = kyc.get_platform_by_id(platform_id)

        if not platform:
            text = 'Выбранной платформы больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        accounts = kyc.get_accounts_by_platform_id(platform_id)

        text = f'<b>Редактирование KYC [{platform.name}]</b>'
        keyboard = self.keyboards.generate_accounts_keyboard(accounts, platform_id)

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Открывает меню редактирования аккаунта
    def kyc_editor_account(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        platform = kyc.get_platform_by_id(account.platform_id)

        text = f'<b>Карточка товара</b>\n\n' \
               f'' \
               f'<b>Платформа:</b> {platform.name}\n' \
               f'<b>Вид аккаунта:</b> {account.name}\n\n' \
               f'' \
               f'<b>Стоимость:</b> {account.price:.2f}$\n' \
               f'<b>Мин. сумма заказа:</b> {account.min_price:.2f}$\n\n' \
               f'' \
               f'<b>Описание:</b> {account.description}\n\n' \
               f'' \
               f'Выберите пункт для изменения на клавиатуре'
        keyboard = self.keyboards.generate_kyc_editor(account)

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Готовит пользователя к замене имени аккаунта, просит прислать новое
    def start_account_name_editing(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        user.update_status('edit_account_name')
        user.update_data({'account_id': account_id})
        self.delete_message(user, message)

        text = 'Отправьте в чат новое имя для вида аккаунта'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает новое имя аккаунта и заменяет его
    def edit_account_name(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account = kyc.get_account_by_id(user.data['account_id'])

        if not account:
            self.remove_keyboard(user)
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account.update_name(message.text)
        self.remove_keyboard(user)

        text = 'Имя аккаунта успешно изменено!'
        keyboard = self.keyboards.generate_back_to_account_button(account)

        self.reload_user(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Готовит пользователя к замене описания аккаунта, просит прислать новое
    def start_account_description_editing(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        user.update_status('edit_account_description')
        user.update_data({'account_id': account_id})
        self.delete_message(user, message)

        text = 'Отправьте в чат новое описание для вида аккаунта\n\n' \
               'Поддерживается любое форматирование, кроме фотографий'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает новое описание для аккаунта
    def edit_account_description(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account = kyc.get_account_by_id(user.data['account_id'])

        if not account:
            self.remove_keyboard(user)
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account.update_description(message.html_text)
        self.remove_keyboard(user)

        text = 'Описание аккаунта успешно изменено!'
        keyboard = self.keyboards.generate_back_to_account_button(account)

        self.reload_user(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Готовит пользователя к замене цены аккаунта, просит прислать новую
    def start_account_price_editing(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        user.update_status('edit_account_price')
        user.update_data({'account_id': account_id})
        self.delete_message(user, message)

        text = 'Отправьте в чат новую стоимость для вида аккаунта'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает и проверяет цену аккаунта
    def edit_account_price(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account = kyc.get_account_by_id(user.data['account_id'])

        if not account:
            self.remove_keyboard(user)
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        try:
            float(message.text)
        except ValueError:
            text = 'Для цены используются целые или дробные числа'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return
        else:
            if float(message.text) <= 0:
                text = 'Цена аккаунта не может быть нулевой или отрицательной'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

        account.update_price(round(float(message.text), 2))
        self.remove_keyboard(user)

        text = 'Цена для вида аккаунта успешно изменена!'
        keyboard = self.keyboards.generate_back_to_account_button(account)

        self.reload_user(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Готовит пользователя к замене мин. стоимости аккаунта, просит прислать новую
    def start_account_min_price_editing(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        user.update_status('edit_account_min_price')
        user.update_data({'account_id': account_id})
        self.delete_message(user, message)

        text = 'Отправьте в чат новую минимальную сумму заказа для вида аккаунта\n\n' \
               '' \
               'Если минимальной суммы заказа быть не должно, отправьте 0'
        keyboard = self.keyboards.cancel

        self.send_message(user, text=text, reply_markup=keyboard)

    # Получает и проверяет новую мин. стоимость аккаунта
    def edit_account_min_price(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.generate_back_to_account_button(account_id=user.data['account_id'])
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        account = kyc.get_account_by_id(user.data['account_id'])

        if not account:
            self.remove_keyboard(user)
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        try:
            float(message.text)
        except ValueError:
            text = 'Для минимальной суммы заказа используются целые или дробные числа'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return
        else:
            if float(message.text) < 0:
                text = 'Минимальная сумма заказа не может быть отрицательной'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

        account.update_min_price(round(float(message.text), 2))
        self.remove_keyboard(user)

        text = 'Минимальная сумма заказа для вида аккаунта успешно изменена!'
        keyboard = self.keyboards.generate_back_to_account_button(account)

        self.reload_user(user)
        self.send_message(user, text=text, reply_markup=keyboard)

    # Готовит пользователя к удалению аккаунта, спрашивает подтверждение
    def delete_account(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        platform = kyc.get_platform_by_id(account.platform_id)

        text = 'Вы уверены, что хотите удалить этот вид аккаунта?\n\n' \
               '' \
               f'<b>Платформа</b>: {platform.name}\n' \
               f'<b>Вид аккаунта</b>: {account.name}'
        keyboard = self.keyboards.generate_delete_account(account)

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    # Удаляет аккаунт
    def delete_account_confirm(self, user, message, account_id):
        account = kyc.get_account_by_id(account_id)

        if not account:
            self.remove_keyboard(user)
            text = 'Выбранного вида аккаунта больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        account.remove()

        text = 'Аккаунт успешно удалён!'
        keyboard = self.keyboards.back_to_platforms

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    def create_platform(self, user, message):
        user.update_status('creating_platform')

        self.delete_message(user, message)
        text = 'Введите имя для новой платформы'
        keyboard = self.keyboards.cancel
        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_platform_name(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_platforms
            self.reload_user(user)
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        self.reload_user(user)
        self.remove_keyboard(user)

        name = message.text.replace('\n', ' ')
        kyc.create_platform(name)

        text = f'Платформа <b>{name}</b> успешно создана!'
        keyboard = self.keyboards.back_to_platforms
        self.send_message(user, text=text, reply_markup=keyboard)

    def delete_platform(self, user, message, platform_id):
        platform = kyc.get_platform_by_id(platform_id)

        if not platform:
            text = 'Этой платформы больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        text = f'Вы уверены, что хотите удалить платформу <b>{platform.name}</b>?\n\n' \
               f'' \
               f'Вместе с этой платформой будут удалены все виды аккаунтов, которые ей принадлежат.'
        keyboard = self.keyboards.generate_delete_platform(platform)
        self.edit_message(user, message, text=text, reply_markup=keyboard)

    def delete_platform_confirm(self, user, message, platform_id):
        platform = kyc.get_platform_by_id(platform_id)

        if not platform:
            text = 'Этой платформы больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        platform.remove()

        text = f'Платформа <b>{platform.name}</b> и все принадлежащие ей аккаунты удалены.'
        keyboard = self.keyboards.back_to_platforms

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    def create_account(self, user, message, platform_id):
        platform = kyc.get_platform_by_id(platform_id)

        if not platform:
            text = 'Этой платформы больше не существует'
            keyboard = self.keyboards.back_to_platforms
            self.edit_message(user, message, text=text, reply_markup=keyboard)
            return

        user.update_status('create_account')
        data = {
            'platform': platform.id,
            'name': None,
            'price': None,
            'min_price': 0,
            'description': None
        }
        user.update_data(data)

        text = f'<b>Создание вида аккаунта</b>\n\n' \
               f'' \
               f'<b>Платформа</b>: {platform.name}\n' \
               f'<b>Название</b>: <i>Нет</i>\n\n' \
               f'' \
               f'<b>Цена</b>: <i>Нет</i>\n' \
               f'<b>Мин. заказ</b>: 0$\n\n' \
               f'' \
               f'<b>Описание</b>: <i>Нет</i>\n'
        keyboard = self.keyboards.account_creator

        self.edit_message(user, message, text=text, reply_markup=keyboard)

    def account_creator(self, user, message, call_id, cdata):
        if cdata == 'cancel':
            platform_id = user.data['platform']
            self.reload_user(user)
            self.kyc_editor_accounts(user, message, platform_id)
        elif cdata == 'name':
            user.update_status('create_account_name')
            self.delete_message(user, message)
            text = 'Отправьте в чат имя для нового вида аккаунта'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
        elif cdata == 'description':
            user.update_status('create_account_description')
            self.delete_message(user, message)
            text = 'Отправьте в чат описание для нового вида аккаунта\n\n' \
                   '' \
                   'Поддреживается любое форматирование, кроме картинок'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
        elif cdata == 'price':
            user.update_status('create_account_price')
            self.delete_message(user, message)
            text = 'Отправьте в чат цену для нового вида аккаунта'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
        elif cdata == 'min_price':
            user.update_status('create_account_min_price')
            self.delete_message(user, message)
            text = 'Отправьте в чат минимальную сумму заказа для нового вида аккаунта\n\n' \
                   '' \
                   'Если минимальной суммы быть не должно, отправьте 0'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
        elif cdata == 'create':
            if not user.data['name'] or not user.data['description'] or not user.data['price']:
                text = 'Новый вид аккаунта не может быть создан без имени, описания или цены'
                self.bot.answer_callback_query(callback_query_id=call_id, text=text, show_alert=True)
                return

            platform = kyc.get_platform_by_id(user.data['platform'])

            if not platform:
                self.reload_user(user)
                text = 'Платформы, в которой вы создавали аккаунт, больше не существует'
                keyboard = self.keyboards.back_to_platforms
                self.edit_message(user, message, text=text, reply_markup=keyboard)
                return

            kyc.create_account(user.data)

            self.reload_user(user)
            text = 'Новый вид аккаунта успешно создан!'
            keyboard = self.keyboards.back_to_platform(platform)
            self.edit_message(user, message, text=text, reply_markup=keyboard)

        elif cdata == 'back':
            platform = kyc.get_platform_by_id(user.data['platform'])

            if not platform:
                self.reload_user(user)
                text = 'Платформы, в которой вы создавали аккаунт, больше не существует'
                keyboard = self.keyboards.back_to_platforms
                self.edit_message(user, message, text=text, reply_markup=keyboard)
                return

            text = f'<b>Создание вида аккаунта</b>\n\n' \
                   f'' \
                   f'<b>Платформа</b>: {platform.name}\n' \
                   f'<b>Название</b>: {user.data["name"] if user.data["name"] else "<i>Нет</i>"}\n\n' \
                   f'' \
                   f'<b>Цена</b>: {str(user.data["price"]) + "$" if user.data["price"] else "<i>Нет</i>"}\n' \
                   f'<b>Мин. заказ</b>: {user.data["min_price"]}$\n\n' \
                   f'' \
                   f'<b>Описание</b>: {user.data["description"] if user.data["description"] else "<i>Нет</i>"}\n'
            keyboard = self.keyboards.account_creator
            self.edit_message(user, message, text=text, reply_markup=keyboard)

    def get_new_account_name(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_creator
            user.update_status('create_account')
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        name = message.text.replace('\n', ' ')

        user.data['name'] = name
        user.update_data(user.data)
        user.update_status('create_account')

        self.remove_keyboard(user)
        text = 'Имя нового вида аккаунта успешно изменено!'
        keyboard = self.keyboards.back_to_creator
        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_account_description(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_creator
            user.update_status('create_account')
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        description = message.html_text

        user.data['description'] = description
        user.update_data(user.data)
        user.update_status('create_account')

        self.remove_keyboard(user)
        text = 'Описание нового вида аккаунта успешно изменено!'
        keyboard = self.keyboards.back_to_creator
        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_account_price(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_creator
            user.update_status('create_account')
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        try:
            float(message.text)
        except ValueError:
            text = 'Для стоимости заказа используются целые или дробные числа'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return
        else:
            if float(message.text) <= 0:
                text = 'Стоимость аккаунта не может быть нулевой или отрицательной'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

        price = round(float(message.text), 2)

        user.data['price'] = price
        user.update_data(user.data)
        user.update_status('create_account')

        self.remove_keyboard(user)
        text = 'Стоимость нового вида аккаунта успешно изменено!'
        keyboard = self.keyboards.back_to_creator
        self.send_message(user, text=text, reply_markup=keyboard)

    def get_new_account_min_price(self, user, message):
        if message.text == 'Отмена ❌':
            self.remove_keyboard(user)
            text = 'Отменено'
            keyboard = self.keyboards.back_to_creator
            user.update_status('create_account')
            self.send_message(user, text=text, reply_markup=keyboard)
            return

        try:
            float(message.text)
        except ValueError:
            text = 'Для минимальной суммы заказа используются целые или дробные числа'
            keyboard = self.keyboards.cancel
            self.send_message(user, text=text, reply_markup=keyboard)
            return
        else:
            if float(message.text) < 0:
                text = 'Стоимость аккаунта не может быть отрицательной'
                keyboard = self.keyboards.cancel
                self.send_message(user, text=text, reply_markup=keyboard)
                return

        price = round(float(message.text), 2)

        user.data['min_price'] = price
        user.update_data(user.data)
        user.update_status('create_account')

        self.remove_keyboard(user)
        text = 'Минимальная сумма заказа нового вида аккаунта успешно изменено!'
        keyboard = self.keyboards.back_to_creator
        self.send_message(user, text=text, reply_markup=keyboard)