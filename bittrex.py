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

from log import Log

log = Log()


BASE_URL = 'https://bittrex.com/api/v1.1/%s/'

MARKET_SET = {'getopenorders', 'cancel', 'sellmarket', 'selllimit', 'buymarket', 'buylimit', 'tradebuy', 'tradesell'}   # 'tradebuy', 'tradesell' are v2
ACCOUNT_SET = {'getorder', 'getbalances', 'getbalance', 'getdepositaddress', 'withdraw', 'getorderhistory'}

HTTP_TIMEOUT = 2
# https://github.com/ericsomdahl/python-bittrex/blob/master/bittrex/bittrex.py
# https://bittrex.com/home/api
# https://github.com/mondeja/bittrex_v2/blob/master/bittrex_v2/bittrex.py

def ts_2_s(ts):
    dot_ix = ts.find('.')
    ts = ts[:dot_ix]
    ts = ts.replace('T', ' ')
    time_struct = time.strptime(ts, '%Y-%m-%d %H:%M:%S')
    return time.mktime(time_struct)


class bittrex:
    def __init__(self, api_key, api_secret):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''

        self.coin_separator = '-'
        self.direct_pairs = ['BTC-XMR', 'USDT-XMR', 'USDT-ZEC', 'BTC-ZEC', 'USDT-BTC', 'BTC-ETH', 'USDT-ETH', 'USDT-ZEC', 'ETH-ZEC', 'ETH-DASH', 'BTC-DASH', 'USDT-DASH', 'ETH-XRP', 'BTC-XRP', 'USDT-XRP', 'BTC-LTC', 'ETH-LTC', 'USDT-LTC', 'BTC-BCC', 'ETH-BCC', 'USDT-BCC', 'BTC-NEO','USDT-NEO', 'BTC-OMG','USDT-OMG' ]
        self.quotes = ['empty quotes']
        self.order_log = {}


    # PUBLIC API FUNCTIONS
    def api_query_public(self, command, req={}):
        '''
        Public API
        '''

        if (command == "returnOrderBook"):
            try:
                ret = requests.get('https://bittrex.com/api/v1.1/public/getorderbook?market=' + str(req['currencyPair']) + '&type=both', timeout=HTTP_TIMEOUT)

                return ret.json()
            except:
                print("|", end='')
                return None
        elif (command == "returnMarketHistory"):
            try:
                ret = requests.get('https://bittrex.com/api/v1.1/public/getmarkethistory?market=' + str(req['currencyPair']), timeout=HTTP_TIMEOUT)

                return ret.json()
            except:
                print("&", end='')
                return None
        else:
            return ""


    def returnOrderBook(self, currencyPair):
        while True:
            res = self.api_query_public("returnOrderBook", {'currencyPair': currencyPair})
            if res is not None:
                break

        res['time'] = time.time()
        return res


    def returnOrderBookCached(self, currencyPair):
        return self.quotes[currencyPair]


    def order_book_aggregated_top1(self, from_coin, to_coin, min_trade, cached = True):
        if cached:
            ob_func = self.returnOrderBookCached
        else:
            ob_func = self.returnOrderBook

        currency_pair = self.coin_separator.join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = ob_func(currency_pair)
            volume = 0
            i = 0
            max_i = len(res['result']['sell'])
            while volume <= min_trade and i < max_i:
                res1 = res['result']['sell'][i]
                price = float(res1['Rate'])
                volume += float(res1['Quantity']) * price
                i += 1

            try:
                return {'price': price, 'volume': volume}       # usdt => eth : usdt-eth => price in usdt, volume in usdt
            except:
                print('min_trade = %d max_i = %d' % (min_trade, max_i))
                print(res['result']['sell'])
                exit()
        else:
            currency_pair = self.coin_separator.join([to_coin, from_coin])
            res = ob_func(currency_pair)
            volume = 0
            i = 0
            max_i = len(res['result']['buy'])
            while volume <= min_trade  and i < max_i:
                res1 = res['result']['buy'][i]
                price = float(res1['Rate'])
                volume += float(res1['Quantity'])
                i += 1

            try:
                return {'price': 1.0 / price, 'volume': volume} # eth => btc: btc-eth => price in eth, volume in eth
            except:
                print('min_trade = %d max_i = %d' % (min_trade, max_i))
                print(res['result']['buy'])
                exit()


    def get_market_history(self, currency_pair):
        res = self.api_query_public('returnMarketHistory', {'currencyPair': currency_pair})

        return res


    def get_market_volatility(self, currency_pair):
        res = self.get_market_history(currency_pair)
        if res is not None:
            history = res['result']


            time0 = ts_2_s(history[0]['TimeStamp'])
            prices = [h['Price'] for h in history if (time0 - ts_2_s(h['TimeStamp'])) < 100]
            max_p = max(prices)
            norm_prices = [p / max_p for p in prices]

            sum_amount = sum([h['Quantity'] for h in history if (time0 - ts_2_s(h['TimeStamp'])) < 100])

            avg_p = sum(norm_prices) / len(norm_prices)
            vol = (sum((p - avg_p) ** 2 for p in norm_prices)) ** 0.5
            return (vol, len(norm_prices), sum_amount)
        else:
            return None


    # PRIVATE API FUNCTIONS
    def api_query_private(self, method, options=None):
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))

        if method in MARKET_SET:
            method_set = 'market'
        elif method in ACCOUNT_SET:
            method_set = 'account'

        request_url = (BASE_URL % method_set) + method + '?'
        request_url += 'apikey=' + self.api_key + "&nonce=" + nonce + '&'
        request_url += urlencode(options)

        try:
            return requests.get(
                request_url,
                headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()},
                timeout=HTTP_TIMEOUT
            ).json()

        except:
            log("ERROR CONNECTING TO EXCHANGE")
            log(request_url)
            return None


    def api_query_private_v2(self, method, options=None):
        BASE_URL2 = BASE_URL = 'https://bittrex.com/api/v2.0/auth/%s/'
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))

        if method in MARKET_SET:
            method_set = 'market'
        elif method in ACCOUNT_SET:
            method_set = 'account'

        request_url = (BASE_URL2 % method_set) + method + '?'
        request_url += 'apikey=' + self.api_key + "&nonce=" + nonce + '&'
        request_url += urlencode(options)

        res =  requests.post(
            request_url,
            headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(),
                                         hashlib.sha512).hexdigest()},
            timeout=HTTP_TIMEOUT
        )
        # TODO: fix error 500. check wrapper on git

        try:
            ...
        except:
            log("ERROR CONNECTING TO EXCHANGE")
            log(request_url)
            return None

    # Ex.: place_order('SELL', 'USDT_BTC', 0.001, 16000, ordertype='CONDITIONAL', timeInEffect=GOOD_TIL_CANCELLED, conditionType="LESS_THAN", target=16001)
    '''
        MarketName:USDT-DASH
        OrderType:LIMIT
        Quantity:0.02352940
        Rate:770.00000000
        TimeInEffect:GOOD_TIL_CANCELLED
        ConditionType:LESS_THAN
        Target:771    
    '''
    def place_order(self, tradetype, market, amount, rate,
                    ordertype, timeInEffect,
                    conditionType=None, target=None):
        """
        Places a buy/sell order with specific conditions
        (target only required if a condition is in place)
        """

        if tradetype in ('BUY', 'buy'):
            method = "tradebuy"
        elif tradetype in ('SELL', 'sell'):
            method = "tradesell"

        if not conditionType:
            conditionType = "CONDITION_NONE"
        if not target:
            target = "0"

        options = {"marketname": market,
                   "ordertype": ordertype,
                   "quantity": str(amount),
                   "rate": str(rate),
                   "timeineffect": str(timeInEffect),
                   "conditiontype": conditionType,
                   "target": target}

        res = self.api_query_private_v2(method, options)

    # PRIVATE API FUNCTIONS
    def create_order(self, from_coin, to_coin, volume, price):
        currency_pair = self.coin_separator.join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.buy_limit(currency_pair, volume, price)

        else:
            currency_pair = self.coin_separator.join([to_coin, from_coin])
            rprice = 1 / price
            rvolume = volume * price
            res = self.sell_limit(currency_pair, rvolume, rprice)

        if res is not None and res["success"]:
            o_id = res["result"]["uuid"]
            # could also store actual amounts for further PL calculations, also time could be useful to benchmark ordr execution time, and freqs of arb ops
            self.order_log[o_id] = {"CurrencyPair": self.coin_separator.join([from_coin, to_coin])}

            return o_id
        else:
            log(res)
            log("FAILED TO CREATE ORDER FOR CONVERSION FROM %s TO %f %s USING PRICE %f" % (from_coin, volume, to_coin, price))
            return -1


    def buy_limit(self, market, quantity, rate):
        log("{} {}".format('buylimit', {'market': market, 'quantity': quantity, 'rate': rate}))
        return self.api_query_private('buylimit', {'market': market, 'quantity': quantity, 'rate': rate})


    def sell_limit(self, market, quantity, rate):
        log("{} {}".format('selllimit', {'market': market, 'quantity': quantity, 'rate': rate}))
        return self.api_query_private('selllimit', {'market': market, 'quantity': quantity, 'rate': rate})


    def cancel_order(self, uuid):
        while True:
            res = self.api_query_private('cancel', {'uuid': uuid})
            if res is not None:
                break

        if res["success"]:
            return True
        else:
            log("FAILED TO CANCEL ORDER %s" % (uuid))

            return False


    def get_open_orders(self, market):
        return self.api_query_public('getopenorders', {'market': market})


    def get_order(self, uuid):
        while True:
            order = self.api_query_private('getorder', {'uuid': uuid})
            if order is not None:
                break

        return order


    def is_order_open(self, uuid):
        order = self.get_order(uuid)
        return order["result"]["IsOpen"]


    def order_remaining_amount(self, uuid):
        exchange_order = self.get_order(uuid)['result']

        logged_order = self.order_log[uuid]
        currency_pair = logged_order["CurrencyPair"]

        if currency_pair in self.direct_pairs:
            amount_to = exchange_order["QuantityRemaining"]
        else:
            amount_from = exchange_order["QuantityRemaining"]
            price = exchange_order["Limit"]

            amount_to = amount_from * price

        return amount_to


    def get_balance(self, currency):
        res = self.api_query_private('getbalance', {'currency': currency})

        if res is not None:
            return res['result']['Balance']
        else:
            return None

#
    def get_ticket(self, from_coin, to_coin, interval='hour'):
        currency_pair = self.coin_separator.join([from_coin, to_coin])
        if currency_pair not in self.direct_pairs:
            currency_pair = self.coin_separator.join([to_coin, from_coin])

        try:
            # https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName=USDT-BTC&tickInterval=day

            ret = requests.get('https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName=' + currency_pair + '&tickInterval=' + interval, timeout=HTTP_TIMEOUT)

            return ret.json()['result']
        except:
            print("|", end='')
            return None

