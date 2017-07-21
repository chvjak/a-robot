import time
import hmac
import hashlib
import requests

try:
    from urllib import urlencode
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urlencode
    from urllib.parse import urljoin

BASE_URL = 'https://bittrex.com/api/v1.1/%s/'

MARKET_SET = {'getopenorders', 'cancel', 'sellmarket', 'selllimit', 'buymarket', 'buylimit'}
ACCOUNT_SET = {'getorder', 'getbalances', 'getbalance', 'getdepositaddress', 'withdraw', 'getorderhistory'}

# https://github.com/ericsomdahl/python-bittrex/blob/master/bittrex/bittrex.py
# https://bittrex.com/home/api


class bittrex:
    def __init__(self, api_key, api_secret):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''

        self.direct_pairs = ['USDT-BTC', 'BTC-ETH', 'USDT-ETH', 'USDT-ZEC', 'ETH-ZEC', 'ETH-DASH', 'BTC-DASH', 'USDT-DASH', 'ETH-XRP', 'BTC-XRP', 'USDT-XRP']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            ret = requests.get('https://bittrex.com/api/v1.1/public/getorderbook?type=both&depth=1&market=' + str(req['currencyPair']))

            return ret.json()
        else:
            return ""

    def api_query1(self, method, options=None):
        """
        Queries Bittrex with given method and options
        :param method: Query method for getting info
        :type method: str
        :param options: Extra options for query
        :type options: dict
        :return: JSON response from Bittrex
        :rtype : dict
        """
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))
        method_set = 'public'

        if method in MARKET_SET:
            method_set = 'market'
        elif method in ACCOUNT_SET:
            method_set = 'account'

        request_url = (BASE_URL % method_set) + method + '?'

        if method_set != 'public':
            request_url += 'apikey=' + self.api_key + "&nonce=" + nonce + '&'

        request_url += urlencode(options)

        return requests.get(
            request_url,
            headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()}
        ).json()


    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}

        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            res1 = res['result']['buy'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            return {'price': float(price), 'volume': volume}
        else:
            currency_pair = "-".join([to_coin, from_coin])
            res = self.returnOrderBook(currency_pair)
            res1= res['result']['sell'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}



    def create_order(self, from_coin, to_coin, volume, price):
        '''
{
"success" : true,
"message" : "",
"result" : {"uuid" : "e606d53c-8d70-11e3-94b5-425861b86ab6"	}
}
        '''

        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.buy_limit(currency_pair, volume, price)

        else:
            currency_pair = "-".join([to_coin, from_coin])

            rprice = 1 / price

            rvolume = volume * price

            res = self.sell_limit(currency_pair, rvolume, rprice)

        print(res)

        if res["success"]:
            return res["result"]["uuid"]
        else:
            # ERROR
            return ""

    def market_order(self, from_coin, to_coin, volume):
        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.sell_market(currency_pair, volume)
        else:
            currency_pair = "-".join([to_coin, from_coin])
            res = self.buy_market(currency_pair, volume)

    def buy_limit(self, market, quantity, rate):
        """
        Used to place a buy order in a specific market. Use buylimit to place
        limit orders Make sure you have the proper permissions set on your
        API keys for this call to work
        /market/buylimit
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query1('buylimit', {'market': market, 'quantity': quantity, 'rate': rate})


    def sell_limit(self, market, quantity, rate):
        """
        Used to place a sell order in a specific market. Use selllimit to place
        limit orders Make sure you have the proper permissions set on your
        API keys for this call to work
        /market/selllimit
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query1('selllimit', {'market': market, 'quantity': quantity, 'rate': rate})

    def sell_market(self, market, quantity):
        """
        Used to place a sell order in a specific market. Use sellmarket to place
        market orders. Make sure you have the proper permissions set on your
        API keys for this call to work
        /market/sellmarket
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query1('sellmarket', {'market': market, 'quantity': quantity})

    def buy_market(self, market, quantity):
        """
        Used to place a buy order in a specific market. Use buymarket to
        place market orders. Make sure you have the proper permissions
        set on your API keys for this call to work
        /market/buymarket
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query1('buymarket', {'market': market, 'quantity': quantity})

    def cancel_order(self, uuid):
        """
        Used to cancel a buy or sell order
        /market/cancel
        :param uuid: uuid of buy or sell order
        :type uuid: str
        :return:
        :rtype : dict
        """
        return self.api_query1('cancel', {'uuid': uuid})

    def get_open_orders(self, market):
        """
        Get all orders that you currently have opened. A specific market can be requested
        /market/getopenorders
        :param market: String literal for the market (ie. BTC-LTC)
        :type market: str
        :return: Open orders info in JSON
        :rtype : dict
        """
        return self.api_query('getopenorders', {'market': market})

    def get_order(self, uuid):
        return self.api_query1('getorder', {'uuid': uuid})

    def is_order_open(self, uuid):
        order = self.get_order(uuid)
        return order["result"]["IsOpen"]

    def order_remaining_amount(self, uuid):
        order = self.get_order(uuid)
        return order["result"]["QuantityRemaining"]





