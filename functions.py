import requests
import pandas as pd
import re
import os
import shutil
from PyQt5 import QtWidgets
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openpyxl import load_workbook

class Func():
    def __init__(self, error_list):
        self.error_list = error_list
    def get_sheets(self):
        API_KEY = os.getenv("API_KEY")
        SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

        # Диапазон
        RANGE_NAME = 'Для парсера!A1:E900'
        service = build('sheets', 'v4', developerKey=API_KEY)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        if not values:
            print('No data found.')
            self.error_list.append("Не найдены данные из гугл таблицы ")
        return values


    def load_models_from_json(self):
        """Загружает список моделей из search.json."""
        with open("search.json", "r", encoding="utf-8") as file:
            search_data = json.load(file)
        models = set()
        for brand in search_data['Type'].values():
            for model_list in brand['Brand'].values():
                models.update(model_list)
        return models

    def get_list_models(self):
        list_model = {}
        list_values_from_sheets = self.get_sheets()
        models_to_search = self.load_models_from_json()  # Получаем список моделей из JSON
        for row_sheets in list_values_from_sheets[1:]:
            try:
                if len(row_sheets) >= 5:  # Проверяем, что строка содержит достаточно данных
                    model = row_sheets[1].strip()  # Артикул модели
                    if model in models_to_search:
                        price = int(re.sub(r'\D', '', row_sheets[2]))
                        list_model[model] = price
            except ValueError:
                self.error_list.append(f"Ошибка в преобразовании цены у модели {row_sheets[0], row_sheets[1], row_sheets[2]} \n")
                continue
        return list_model

    def find_model_on_site(self):
        try:
            if os.path.isfile("result.xlsx"):
                os.remove("result.xlsx")

            if os.path.exists("Result"):
                shutil.rmtree("Result")
        except PermissionError as pe:
            QtWidgets.QMessageBox.information(None, "Ошибка", "Не удается удалить старые файлы отчетов. \n Проверьте не открыт ли файл")
            return
        list_data = []
        list_models = self.get_list_models() # получаем список моделей из гугл таблицы которые нужно искать на сайте

        for article in list_models.keys():
            query_url = f'https://catalog.onliner.by/sdapi/catalog.api/search/products?query={article}'
            try:
                get_find_model = requests.get(query_url, timeout=7).json()
                if get_find_model['products'] == []:
                    self.error_list.append('модель ' + article + ' не найдена по запросу ' + query_url)
                else:
                    try:
                        link_offers = get_find_model['products'][0]['prices']['html_url']
                        name = get_find_model['products'][0]['full_name']
                        price_from_sheets = list_models[article]
                        list_data = self.parse_one_model(link_offers, name, list_data, article, price_from_sheets)
                    except TypeError as e:
                        self.error_list.append(f'Не найдены предложения продавцов для модели {article}, {query_url}; Ошибка {e} ' )
                        continue
            except Exception as e:
                pass
        try:
            df_info = pd.DataFrame(list_data, columns=['shop'
                , 'article'
                , 'name'
                , 'amount'
                , 'price_from_sheets'
                , 'link'
                , 'diff'])
            df_info = df_info.sort_values(by='shop', ascending=False)
            df_info = df_info.rename(columns={"shop": "Магазин",
                                    "article": "Артикул",
                                    "name": "Наименование товара",
                                    "amount": "Цена магазина",
                                    "price_from_sheets": "РРЦ",
                                    "link": "Ссылка на товар в каталоге",
                                    "diff": "Разница в цене"
                                    })

            self.SplitFile(df_info, "Магазин")
            output_file = 'result.xlsx'
            df_info.to_excel(output_file, index=False)
            self.adjust_column_width(output_file)
            self.Save_Errors()
            QtWidgets.QMessageBox.information(None, "Успех", "Файлы отчетов сохранены в папке: Result")
        except Exception as e:
            self.error_list.append(f'Отчет не создан. Ошибка {e} ')

    def adjust_column_width(self, file_path):
        """Настраивает ширину столбцов в Excel-файле в соответствии с содержимым."""
        wb = load_workbook(file_path)
        ws = wb.active

        for col in ws.columns:
            max_length = 0
            column_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = max_length + 2
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(file_path)

    def parse_one_model(self, link_offers, name, list_data, intresting_model, price_from_sheets):
        try:
            start_str = 'https://catalog.onliner.by/conditioners/'
            end_str = '/prices'
            start_index = link_offers.find(start_str)
            start_index += len(start_str)
            end_index = link_offers.find(end_str)
            dev_id = link_offers[start_index:end_index]
            slash_index = dev_id.find('/')
            dev_id = dev_id[slash_index + 1:]
            xhr_url = f'https://catalog.onliner.by/sdapi/shop.api/products/{dev_id}/positions?town=all&has_prime_delivery=1&town_id=17030'
            get_all_offers_XHR = requests.get(xhr_url).json()
            list_data = self.add_to_lst(get_all_offers_XHR, name, link_offers, list_data, intresting_model, price_from_sheets)
        except Exception as e:
            self.error_list.append(f'Неудачный запрос {xhr_url}. Ошибка {e} ')
        return list_data

    def add_to_lst(self, get_all_offers_XHR, name, link_offers, list_data, intresting_model,price_from_sheets):
        def find_name_prod(shop_id):
            return get_all_offers_XHR['shops'][f'{shop_id}']['title']
        try:
            for row in get_all_offers_XHR['positions']['primary']:
                keys_to_keep = ['product_id', 'article', 'shop_id']
                filtered_dict = {key: row[key] for key in keys_to_keep if key in row}

                filtered_dict['amount'] = self.custom_round(row['position_price']['amount'])
                filtered_dict['price_from_sheets'] = price_from_sheets
                filtered_dict['diff'] = int(filtered_dict['price_from_sheets']) - int(filtered_dict['amount'])
                if filtered_dict['diff'] <= 1:
                    continue
                filtered_dict['shop'] = find_name_prod(filtered_dict['shop_id'])
                filtered_dict['name'] = name
                filtered_dict['link'] = link_offers
                if filtered_dict['article'] == '':
                    filtered_dict['article'] = intresting_model
                del filtered_dict['shop_id']
                del filtered_dict['product_id']

                list_data.append(filtered_dict)
        except Exception as a:
            self.error_list.append('Ошибка при получении информации по модели '+ intresting_model + a)
        return list_data

    def custom_round(self, number_str):
        number_str = number_str.replace(',', '.').strip()
        # Преобразуем строку в число с плавающей точкой
        number = float(number_str)
        integer_part = int(number)
        fractional_part = number - integer_part
        # Округляем по заданным правилам
        if fractional_part == 0.5:
            return integer_part + 1

        return round(number)

    def Save_Errors(self):
        with open('errors.txt', 'w+') as ef:
            for i in self.error_list:
                ef.write(i + '\n')

    def SplitFile(self, df, column_name):
        grouped = df.groupby(column_name)
        output_dir = "Result"
        os.makedirs(output_dir, exist_ok=True)

        for group_name, group_df in grouped:
            sanitized_key = self.replace_symbols(str(group_name))
            group_df.to_excel(os.path.join(output_dir, f"{sanitized_key}.xlsx"), index=False)
            self.adjust_column_width(os.path.join(output_dir, f"{sanitized_key}.xlsx"))

    def replace_symbols(self, txt):

        forbidden = '\\/~!@#$%^&*=|`\'""'
        for char in forbidden:
            txt = txt.replace(char, '_')
        return txt


