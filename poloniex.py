import requests
import json
import time
import hmac, hashlib


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class poloniex:
    def __init__(self, APIKey="", Secret=""):
        self.APIKey = APIKey
        self.Secret = Secret

        self.coin_separator = '_'
        self.direct_pairs = ['USDT_BTC', 'BTC_ETH', 'USDT_ETH', 'USDT_ZEC', 'ETH_ZEC', 'BTC_XRP', 'USDT_XRP', 'BTC_BCH', 'USDT_BCH']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            ret = requests.get('https://poloniex.com/public?command=returnOrderBook&depth=1&currencyPair=' + str(req['currencyPair']))
            return ret.json()
        else:
            req['command'] = command
            req['nonce'] = int(time.time() * 1000)
            post_data = req

            sign = hmac.new(self.Secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.APIKey
            }

            ret = requests.post('https://poloniex.com/tradingApi', data = post_data, headers = headers)
            return ret.json()

    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def returnOrderBookCached(self, currencyPair):
        return self.quotes[currencyPair]

    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}

        currency_pair = "_".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBookCached(currency_pair)
            price, volume = res['asks'][0]
            price = float(price)
            return {'price': float(price), 'volume': volume}
        else:
            currency_pair = "_".join([to_coin, from_coin])
            res = self.returnOrderBookCached(currency_pair)
            price, volume = res['bids'][0]
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}



