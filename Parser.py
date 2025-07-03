import requests
import pandas as pd
import re
import json
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os


def get_sheets():

    load_dotenv()

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
        error_file.write("Не найдены данные из гугл таблицы \n")
    return values



class MainWindow:
    def __init__(self, master):
        self.master = master
        self.type_list  = []
        self.brand_list = []
        self.model_list = []
        # self.enable_eq_result = 1

    def CreateMainWindow(self):

        self.bnt_start = tk.Button(self.master, text="Запустить", command=self.find_model_on_site)
        self.bnt_start.place(relx=0.5, rely=0.8, anchor=tk.CENTER)
        self.txt = tk.Text(width=25, height=5)
        self.txt.place(relx=0.2, rely=0.4, anchor=tk.NW)

        type = ["Кондиционеры", "Мойки воздуха", "Увлажнители воздуха"]
        self.combobox = ttk.Combobox(values=type, width=25)
        self.combobox.place(relx=0.2, rely=0.2, anchor=tk.NW)

        brand = ["Royal Clima", "Mitsudai", "CHiQ"]
        self.combobox1 = ttk.Combobox(values=brand, width=25)
        self.combobox1.place(relx=0.2, rely=0.3, anchor=tk.NW)



    def get_list_model(self):
        list_model = {}
        list_values_from_sheets = get_sheets()
        # print(list_values_from_sheets)
        for row_sheets in list_values_from_sheets[1:]:
            try:
                if len(row_sheets) == 5:
                    if (row_sheets[0] == 'Кондиционер Royal Clima' or row_sheets[0] == 'Кондиционер Mitsudai'
                            or row_sheets[0] == 'Кондиционер CHiQ' or row_sheets[0] == 'Кондиционер LEGION'):
                        list_model[(row_sheets[1].strip())] = int(
                            re.sub(r'\D', '', row_sheets[2]))  # получили список интересующих моделей и цену на них
            except ValueError as e:
                error_file.write(f"Ошибка в преобразовании цены у позиции {row_sheets[0], row_sheets[1], row_sheets[2]} \n" )

                continue
        return list_model

    def find_model_on_site(self):
        # self.enable_eq_result = self.enabled.get()
        # print(self.enable_eq_result)
        # type = combobox.get()
        self.GetModel()
        list_model = self.get_list_model()
        df_info = pd.DataFrame(columns=['product_id'
                                        ,'shop'
                                        ,'article'
                                        ,'name'
                                        ,'amount'
                                        ,'link'
                                        ,'price_from_sheets'
                                        , 'diff'])
        # not_found = []
        i = 0
        for article in list_model.keys():
            # print('article', article)
            query_url = f'https://catalog.onliner.by/sdapi/catalog.api/search/products?query={article}'
            try:
                get_find_model = requests.get(query_url, timeout=7)
            except Exception as e:

                print(e)
            if get_find_model['products'] == []:
                error_file.write(f"На сайте не найден артикул {article}, по запросу {query_url} \n")
                i += 1
            else:
                print(get_find_model)
                try:
                    link_offers = get_find_model['products'][0]['prices']['html_url']
                    name = get_find_model['products'][0]['full_name']
                    price_from_sheets = list_model[article]
                    df_info = self.parse_one_model(link_offers, name, df_info, article, price_from_sheets)
                except TypeError as e:
                    i += 1
                    print('ошибка', e)

                    error_file.write(f"Не найден артикул {article} \n")
                    continue

        df_info = df_info.sort_values(by='shop', ascending=False)
        df_info.to_excel('result.xlsx')
        messagebox.showinfo("Уведомление", f"Отчет создан")

    def parse_one_model(self, link_offers, name, df_info, intresting_model, price_from_sheets):
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
        df_info = self.add_to_df(get_all_offers_XHR, name, link_offers, df_info, intresting_model, price_from_sheets)
        return df_info

    def add_to_df(self, get_all_offers_XHR, name, link_offers, df_info, intresting_model,price_from_sheets):
        def find_name_prod(shop_id):
            name_prod = get_all_offers_XHR['shops'][f'{shop_id}']['title']
            return name_prod

        for row in get_all_offers_XHR['positions']['primary']:
            keys_to_keep = ['product_id', 'article', 'shop_id']
            filtered_dict = {key: row[key] for key in keys_to_keep if key in row}
            filtered_dict['shop'] = find_name_prod(filtered_dict['shop_id'])
            filtered_dict['amount'] = self.custom_round(row['position_price']['amount'])
            filtered_dict['name'] = name
            filtered_dict['link'] = link_offers
            if filtered_dict['article'] == '':
                filtered_dict['article'] = intresting_model
            main_price = price_from_sheets
            filtered_dict['price_from_sheets'] = main_price
            filtered_dict['diff'] = int(filtered_dict['price_from_sheets']) - int(filtered_dict['amount'])
            df_info = df_info._append(filtered_dict, ignore_index=True)

        return df_info


    def custom_round(self, number_str):
        number_str = number_str.replace(',', '.').strip()
        # Преобразуем строку в число с плавающей точкой
        number = float(number_str)
        integer_part = int(number)
        fractional_part = number - integer_part

        if fractional_part == 0.5:
            return integer_part + 1

        return round(number)

    def GetModel(self):
        with open("search.json", 'r', encoding='utf-8') as f:
            searchlist = json.load(f)
        self.type_list = (list(searchlist['Type'].keys()))


def main():
    try:
        root = tk.Tk()
        root.geometry("350x260")
        root.title("Парсер ONLINER")
        root.resizable(width=False, height=False)
        app = MainWindow(root)
        app.CreateMainWindow()
        root.mainloop()
    except Exception as e:
        error_file.write(f"Ошибка при выполнении {e}")
    error_file.close()


if __name__ == "__main__":
    error_file = open('errors.txt', 'w+')
    #main()