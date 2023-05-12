import pygsheets
from datetime import datetime

months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


class Sheet:
    def __init__(self, key, token):
        now = datetime.now().month
        gs = pygsheets.authorize(service_file=token)
        self.table = gs.open_by_key(key)
        try:
            self.table.worksheet(property='title', value=months[now - 1])
        except pygsheets.exceptions.WorksheetNotFound:
            self.create_worksheet()

    def create_worksheet(self):
        now = datetime.now().month
        year = datetime.now().year
        ws = self.table.add_worksheet(title=months[now - 1])

        bold_cell = pygsheets.Cell('A1')
        bold_cell.set_text_format('bold', True)
        title_range = ws.range('A1:E1', returnas='range')
        title_range.apply_format(bold_cell)

        colored_currency = pygsheets.Cell('A1')
        colored_currency.set_text_format('foregroundColor', (0.2, 0.66, 0.33, 1))
        colored_currency.format = (pygsheets.FormatType.CURRENCY, '$#,##0.00_);($#,##0.00)')
        currency_range = ws.range('D2:D100', returnas='range')
        currency_range.apply_format(colored_currency)

        ws.range('A1:A', returnas='range').update_borders(right=True, style='SOLID')
        ws.range('B1:B', returnas='range').update_borders(right=True, style='SOLID')
        ws.range('C1:C', returnas='range').update_borders(right=True, style='SOLID')
        ws.range('D1:D', returnas='range').update_borders(right=True, style='SOLID')
        ws.range('E1:E', returnas='range').update_borders(right=True, style='SOLID')
        ws.range('A1:E1', returnas='range').update_borders(bottom=True, style='SOLID')

        ws.update_row(1, ['Username', 'Платформа', 'Вид', 'USD', 'Заказ'])
        ws.adjust_column_width(start=5, end=5, pixel_size=115)
        ws.adjust_column_width(start=8, end=8, pixel_size=140)

        cell = ws.cell('H2')
        cell.value = '=COUNTA(A2:A)'
        cell = ws.cell('H3')
        cell.value = '=SUM(D2:D)'
        cell.format = (pygsheets.FormatType.CURRENCY, '$#,##0.00_);($#,##0.00)')

        cell = ws.cell('G2')
        cell.set_text_format('bold', True)
        cell.value = 'Всего заказов:'
        cell = ws.cell('G3')
        cell.set_text_format('bold', True)
        cell.value = 'Общая сумма:'

        ws.adjust_column_width(start=10, end=10, pixel_size=110)

    def get_free_row(self):
        now = datetime.now().month - 1
        try:
            ws = self.table.worksheet(property='title', value=months[now])
        except pygsheets.exceptions.WorksheetNotFound:
            self.create_worksheet()
            ws = self.table.worksheet(property='title', value=months[now])

        rows = ws.get_col(1)
        for i in range(len(rows)):
            if not rows[i]:
                return i + 1
        return -1

    def insert_order(self, username, platform, account, value, amount):
        now = datetime.now().month - 1
        try:
            ws = self.table.worksheet(property='title', value=months[now])
        except pygsheets.exceptions.WorksheetNotFound:
            self.create_worksheet()
            ws = self.table.worksheet(property='title', value=months[now])

        row = self.get_free_row()
        values = [username, platform, account, value, amount]
        ws.update_row(index=row, values=values)
