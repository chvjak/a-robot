import requests
import json
import time
import hmac, hashlib


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class poloniex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

        self.direct_pairs = ['USDT_BTC', 'BTC_ETH', 'USDT_ETH', 'USDT_ZEC', 'ETH_ZEC']


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

    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}

        currency_pair = "_".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            price, volume = res['asks'][0]
            price = float(price)
            return {'price': float(price), 'volume': volume}
        else:
            currency_pair = "_".join([to_coin, from_coin])
            res = self.returnOrderBook(currency_pair)
            price, volume = res['bids'][0]
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}

    # Returns all of your balances.
    # Outputs:
    # {"BTC":"0.59098578","LTC":"3.31117268", ... }
    def returnBalances(self):
        return self.api_query('returnBalances')

    # Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self, currencyPair):
        return self.api_query('returnOpenOrders', {"currencyPair": currencyPair})

    # Places a buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is buying at
    # amount        Amount of coins to buy
    # Outputs:
    # orderNumber   The order number
    def buy(self, currencyPair, rate, amount):
        if currencyPair in direct_pairs:
            return self.api_query('buy', {"currencyPair": currencyPair, "rate": rate, "amount": amount})
        elif currencyPair in reversed_pairs:
            return self.api_query('sell', {"currencyPair": currencyPair, "rate": rate, "amount": amount})


    # Outputs:
    # succes        1 or 0
    def cancel(self, currencyPair, orderNumber):
        return self.api_query('cancelOrder', {"currencyPair": currencyPair, "orderNumber": orderNumber})

