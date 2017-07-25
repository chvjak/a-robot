import requests
import json
import time
import hmac, hashlib


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class bitfinex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret
        self.coin_separator = ''
        self.direct_pairs = ['BTCUSD', 'ETHBTC', 'ETHUSD']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            ret = requests.get('https://api.bitfinex.com/v1/book/' + str(req['currencyPair']) +'?limit_bids=1&limit_asks=1')
            return ret.json()
        else:
            return ""

    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def returnOrderBookCached(self, currencyPair):
        return self.quotes[currencyPair]

    def order_book_top10(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}
        currency_pair_list = [from_coin, to_coin]

        currency_pair = "".join(currency_pair_list)
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            a = res['asks'][0]
            price, volume = a['price'], a['amount']
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "".join(reversed(currency_pair_list))
            res = self.returnOrderBook(currency_pair)
            b = res['bids'][0]
            price, volume = b['price'], b['amount']
            price = float(price)
            return {'price': float(price), 'volume': volume}

    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}
        currency_pair_list = [from_coin, to_coin]

        currency_pair = "".join(currency_pair_list)
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBookCached(currency_pair)
            a = res['asks'][0]
            price, volume = a['price'], a['amount']

            price = float(price)
            volume = float(volume)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "".join(reversed(currency_pair_list))
            res = self.returnOrderBookCached(currency_pair)
            b = res['bids'][0]
            price, volume = b['price'], b['amount']
            price = float(price)
            volume = float(volume)
            return {'price': float(price), 'volume': volume}


