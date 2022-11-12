import requests
import base64
import time
import hmac
import os
import hashlib
import pandas as pd
import ast
import json
import csv
from requests.exceptions import HTTPError
from datetime import datetime
import math

def write_to_log(*data):
    if data:
        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open("trans_log.txt", "a") as myfile:
            myfile.write(f'[{dt_string}] {data[0]}\n')
    else:
        with open("trans_log.txt", "a") as myfile:
            myfile.write('\n')


class Loan:
    def __init__(self, coin, delete_orders_older_than_hours):
        self.all_currencies = None
        self.current_lending_rates = None
        self.last_price = None
        self.account_balance = None
        self.url = None
        self.api_secret = None
        self.api_passphrase = None
        self.api_key = None
        self.api_name = None
        self.open_orders = pd.DataFrame()
        self.coin = coin
        self.precision = None
        self.min_USDT_amount = 10
        self.delete_orders_older_than_hours = delete_orders_older_than_hours
        self.get_os_vars()
        self.get_currency_precision()

    def get_os_vars(self):
        self.api_name = os.environ.get("API_NAME")
        self.api_key = os.environ.get("API_KEY")
        self.api_passphrase = os.environ.get("API_PASSPHRASE")
        self.api_secret = os.environ.get("API_SECRET")
        self.url = 'https://api.kucoin.com'  #
        self.start_log()

    def start_log(self):
        write_to_log()
        write_to_log(f'----------Created {self.coin} instance, deleting orders older than {self.delete_orders_older_than_hours} hours----------')

    def get_lending_rates(self):
        point = f'/api/v1/margin/market?currency={self.coin}&term=7'
        call_type = 'GET'
        response = self.call_kucoin(point, call_type)
        self.current_lending_rates = pd.DataFrame(response['data'])
        # self.current_lending_rates.to_csv(f'{self.coin}_current_lending_rates.csv')
        if len(self.current_lending_rates) == 0:  # no lending rates available
            write_to_log(f'Cannot lend {self.coin} no lending rates available, adding to unlendable.csv')

            with open("unlendable.csv", "a") as myfile:
                myfile.write(f'{self.coin}\n')
            return False
        else:
            return True

    def get_available_balance(self):
        point = f'/api/v1/accounts?currency=' + self.coin
        call_type = 'GET'
        response = self.call_kucoin(point, call_type)
        self.account_balance = pd.DataFrame(response['data'])
        self.account_balance = self.account_balance.loc[self.account_balance['type'] == 'main']
        # self.account_balance.to_csv(f'{self.coin}_account_balance_data.csv')
        write_to_log(f'{round(float(self.account_balance["available"]), 2)} {self.coin} available for lending, lend precision {self.precision}')
        return float(self.account_balance['available'])

    def lend_coin(self):
        def truncate_amt(amount, precision):
            decimal_places = str(precision)
            chopping = decimal_places.find('.')
            if chopping == -1:
                amount = int(float(amount))
            else:
                decimal_places = len(decimal_places.replace('.', ' ').split()[-1])
                amount = math.floor(float(amount) * 10 ** decimal_places) / 10 ** decimal_places
            return amount

        def split_amount(amt, precision):
            for i in range(3, 0, -1):
                amount = amt / i
                if amount >= float(precision):
                    return [i, truncate_amt(amount, precision)]
            return None

        if self.get_lending_rates():
            coins_available = self.get_available_balance()
            split_amounts = split_amount(coins_available, self.precision)

            if split_amounts is not None:
                for i in range(split_amounts[0]):
                    lend_interest_rate_daily = self.current_lending_rates.iloc[0]['dailyIntRate']

                    lend_interest_rate_daily = format(float(lend_interest_rate_daily) + i * 0.00001, '.5f')
                    # lend_interest_rate_daily = format(lend_interest_rate_daily, '.5f')

                    # print(lend_amount)
                    lend_amount = split_amounts[1]
                    # print(lend_amount)
                    # print(type(lend_amount))
                    if lend_amount > 0:
                        order_nbr = self.place_order(lend_amount, lend_interest_rate_daily)
                        if order_nbr.json()['code'] == '400100':
                            write_to_log(f'Failed Lending {lend_amount} {self.coin}, coin precision was unknown, recorded in min_lend_amount.json for future use')
                            write_to_log(order_nbr.json()['code'])
                            write_to_log(order_nbr.json()['msg'])
                            pass
                        if 'data' in order_nbr.json():
                            a = order_nbr.json()['data']
                            a = a['orderId']
                            apr = float(lend_interest_rate_daily) * 365 * 100
                            write_to_log(f'Lending {lend_amount} {self.coin}, @ {lend_interest_rate_daily}% daily ({round(apr, 2)}%APR), 7 days, order {a}')
                    else:
                        write_to_log(f'Cannot lend {self.coin}, amount > USDT10 but after conversion {lend_amount} {self.coin}')
        # else:
        #     write_to_log(f'unable to lend, only {round(USDT_funds_available, 2)} USDT available')

    def get_last_price(self):
        point = '/api/v1/market/orderbook/level1?symbol=' + self.coin + '-USDT'
        call_type = 'GET'
        response = self.call_kucoin(point, call_type)
        self.last_price = response['data']['price']
        return float(self.last_price)

    def cancel_old_orders(self):
        call_type = 'DELETE'
        df = self.open_orders
        time_in_secs = float(60 * 60 * self.delete_orders_older_than_hours)
        today = time.time()
        compare_date = (today - time_in_secs) * 1000

        self.get_lending_rates() # happens twice, clean it up
        lend_interest_rate_daily = self.current_lending_rates.iloc[0]['dailyIntRate']
        lowest_rate = format(float(lend_interest_rate_daily), '.5f')
        for index in range(len(df)):
            dict_order = df['items'].loc[index]
            # print(dict_order['dailyIntRate'], lowest_rate) ####
            #if order on top of queue, leave it
            if dict_order['dailyIntRate'] == lowest_rate:
                # print(f'skipping this one')
                write_to_log(f'not deleting {dict_order["orderId"]}, currently at lowest available rate {lowest_rate}% daily')
                continue
            created = float(dict_order['createdAt'])
            if created < compare_date:
                point = '/api/v1/margin/lend/' + dict_order["orderId"]
                response = self.call_kucoin(point, call_type)
                write_to_log(f'deleted order {dict_order["orderId"]}')

    def process_open_orders(self):
        point = '/api/v1/margin/lend/active?currency=' + self.coin + '&currentPage=1&pageSize=50'
        call_type = 'GET'

        response = self.call_kucoin(point, call_type)
        self.open_orders = pd.DataFrame(response['data'])

        if self.open_orders.shape[0] > 0:
            self.cancel_old_orders()

    def call_kucoin(self, point, call_type):
        url = self.url + point
        now = int(time.time() * 1000)
        str_to_sign = str(now) + call_type + point
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode("utf-8"), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2"
        }
        try:
            response = requests.request(call_type, url, headers=headers)
            response.raise_for_status()
            return response.json()
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            print(response)
        except Exception as err:
            print(f'Other error occurred: {err}')
        # todo check for empty json

    def place_order(self, amount, interest):
        point = '/api/v1/margin/lend'
        # print(amount)
        # amount = self.format_amount(amount, self.precision)
        # print(amount)
        # print(type(amount))
        # if amount == 0:
        #     print('cannot place order')
        data = {"currency": self.coin,
                "size": amount,
                "dailyIntRate": interest,
                "term": 7}
        # exit()
        data_json = json.dumps(data)
        # print(data_json)

        now = int(time.time() * 1000)
        str_to_sign = str(now) + 'POST' + '/api/v1/margin/lend' + data_json
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "API_SECRET": self.api_secret,
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"  # specifying content type or using json=data in request
        }
        response = requests.request('post', self.url + point, headers=headers, data=data_json)
        # print(response)
        # print(response.json())
        if response.json()['code'] == '400100':  # add coin to precision file, check if not another error
            err_msg = response.json()['msg'].split()
            if (err_msg[0] + err_msg[1]) == 'lendsize':
                # print('lend size error')
                self.precision = err_msg[5]
            else:
                # print('found new precision')
                self.precision = response.json()['msg'].split()[-1]

            f = open('min_lend_amount.json')
            dict_lend = json.load(f)
            f.close()
            dict_lend[self.coin] = self.precision
            with open('min_lend_amount.json', 'w') as convert_file:
                convert_file.write(json.dumps(dict_lend))
            write_to_log(f'min_lend_amount.json updated with new entry {self.coin} precision {self.precision}')

        return response

    def get_currency_precision(self):
        # print(f'getting curr precision {self.coin}')
        if not os.path.isfile('min_lend_amount.json'):
            self.precision = 0.1
            dict_lend = {self.coin: self.precision}
            with open('min_lend_amount.json', 'w') as convert_file:
                convert_file.write(json.dumps(dict_lend))
            write_to_log(f'min_lend_amount.json does not exist, defaulting to precision of 0.1')
        else:
            f = open('min_lend_amount.json')
            dict_lend = json.load(f)
            f.close()
            # print(dict_lend)
            if self.coin in dict_lend:
                self.precision = dict_lend[self.coin]
            else:
                self.precision = 0.1  # will get overwritten later if wrong
                dict_lend[self.coin] = self.precision
                with open('min_lend_amount.json', 'w') as convert_file:
                    convert_file.write(json.dumps(dict_lend))
                write_to_log(f'adding {self.coin} to min_lend_amount.json with default precision of 0.1')
        # print(f'precision = {self.precision}')


    def format_amount(self, amount, decimal_places):
        def truncate(amt, dec_places):
            return math.floor(amt * 10 ** dec_places) / 10 ** dec_places

        decimal_places = str(decimal_places)
        chopping = decimal_places.find('.')
        if chopping == -1:
            # precision = 1
            amount = int(float(amount))
        else:
            decimal_places = len(decimal_places.replace('.', ' ').split()[-1])
            amount = truncate(float(amount), decimal_places)
        return amount


def get_my_coins_list():
    exceptions_list = []
    if os.path.isfile('unlendable.csv'):
        with open('unlendable.csv', 'r') as myfile:
            for row in myfile:
                exceptions_list.append(row.rstrip('\n'))
    else:
        write_to_log(f'unlendable.csv does not exist, will be created as need be')

    api_name = os.environ.get("API_NAME")
    api_key = os.environ.get("API_KEY")
    api_passphrase = os.environ.get("API_PASSPHRASE")
    api_secret = os.environ.get("API_SECRET")
    url = 'https://api.kucoin.com'  #

    point = '/api/v1/accounts'
    call_type = 'GET'
    url = url + point

    now = int(time.time() * 1000)
    str_to_sign = str(now) + call_type + point
    signature = base64.b64encode(
        hmac.new(api_secret.encode("utf-8"), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
    passphrase = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": api_key,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2"
    }
    response = requests.request(call_type, url, headers=headers)

    my_list = []
    for i in response.json()['data']:
        if i['type'] == 'main' and (float(i['balance']) > 0 or float(i['available']) > 0 or float(i['holds']) > 0):
            my_list.append(i['currency'])
    my_list = [i for i in my_list if i not in exceptions_list]
    return my_list
