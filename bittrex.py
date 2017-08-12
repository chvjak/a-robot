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

HTTP_TIMEOUT = 2
# https://github.com/ericsomdahl/python-bittrex/blob/master/bittrex/bittrex.py
# https://bittrex.com/home/api


class bittrex:
    def __init__(self, api_key, api_secret):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''

        self.coin_separator = '-'
        self.direct_pairs = ['USDT-BTC', 'BTC-ETH', 'USDT-ETH', 'USDT-ZEC', 'ETH-ZEC', 'ETH-DASH', 'BTC-DASH', 'USDT-DASH', 'ETH-XRP', 'BTC-XRP', 'USDT-XRP', 'BTC-LTC', 'ETH-LTC', 'USDT-LTC', 'BTC-BCC', 'ETH-BCC', 'USDT-BCC', 'BTC-NEO','USDT-NEO', 'BTC-XMR','USDT-XMR' ]
        self.quotes = ['empty quotes']
        self.order_log = {}

    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            try:
                ret = requests.get('https://bittrex.com/api/v1.1/public/getorderbook?market=' + str(req['currencyPair'] + '&type=both'), timeout=HTTP_TIMEOUT)

                return ret.json()
            except:
                print("ERROR CONNECTING TO EXCHANGE")
                print('https://bittrex.com/api/v1.1/public/getorderbook?market=' + str(req['currencyPair'] + '&type=both'))
                return None
        else:
            return ""

    def api_query1(self, method, options=None):
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

        try:
            return requests.get(
                request_url,
                headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()},
                timeout=HTTP_TIMEOUT
            ).json()



        except:
            print("ERROR CONNECTING TO EXCHANGE")
            print(request_url)
            return None

    def returnOrderBook(self, currencyPair):
        res = self.api_query("returnOrderBook", {'currencyPair': currencyPair})
        if res is not None:
            res['time'] = time.time()
        return res

    def returnOrderBookCached(self, currencyPair):
        return self.quotes[currencyPair]

    def order_book_top1(self, from_coin, to_coin, cached = True):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}
        if cached:
            ob_func = self.returnOrderBookCached
        else:
            ob_func = self.returnOrderBook

        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = ob_func(currency_pair)
            self.quotes[currency_pair] = res

            res1 = res['result']['sell'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            return {'price': price, 'volume': volume * price}       # usdt => eth : usdt-eth => price in usdt, volume in usdt
        else:
            currency_pair = "-".join([to_coin, from_coin])
            res = ob_func(currency_pair)
            self.quotes[currency_pair] = res

            res1 = res['result']['buy'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume} # eth => btc: btc-eth => price in eth, volume in eth

    def order_book_aggregated_top1(self, from_coin, to_coin, min_trade, cached = True):
        if cached:
            ob_func = self.returnOrderBookCached
        else:
            ob_func = self.returnOrderBook

        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = ob_func(currency_pair)
            volume = 0
            i = 0
            while volume < min_trade:
                res1 = res['result']['sell'][i]
                price = float(res1['Rate'])                 # 2DO: MAX price is used instead of WEIGHTED
                volume += float(res1['Quantity']) * price
                i += 1
            return {'price': price, 'volume': volume}       # usdt => eth : usdt-eth => price in usdt, volume in usdt
        else:
            currency_pair = "-".join([to_coin, from_coin])
            res = ob_func(currency_pair)
            self.quotes[currency_pair] = res
            volume = 0
            i = 0
            while volume < min_trade:
                res1 = res['result']['buy'][i]
                price = float(res1['Rate'])                # 2DO: MAX price is used instead of WEIGHTED
                volume += float(res1['Quantity'])
                i += 1

            return {'price': 1.0 / price, 'volume': volume} # eth => btc: btc-eth => price in eth, volume in eth


    def create_order(self, from_coin, to_coin, volume, price):
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
            o_id = res["result"]["uuid"]

            # could also store actual amounts for further PL calculations, also time could be useful to benchmark ordr execution time, and freqs of arb ops
            self.order_log[o_id] = {"CurrencyPair": "-".join([from_coin, to_coin])}

            return o_id
        else:
            print("FAILED TO CREATE ORDER FOR CONVERSION FROM %s TO %f %s USING PRICE %f" % (from_coin, volume, to_coin, price))
            return -1

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
        order = self.api_query1('getorder', {'uuid': uuid})
        #print(order)
        return order

    def is_order_open(self, uuid):
        order = self.get_order(uuid)
        if order is not None:
            return order["result"]["IsOpen"]
        else:
            return True


    def order_remaining_amount(self, uuid):
        exchange_order = self.get_order(uuid)['result']

        logged_order = self.order_log[uuid]
        currency_pair = logged_order ["CurrencyPair"]

        if currency_pair in self.direct_pairs:
            amount_to = exchange_order["QuantityRemaining"]
        else:
            amount_from = exchange_order["QuantityRemaining"]
            price = exchange_order["Limit"]

            amount_to = amount_from * price

        return amount_to
