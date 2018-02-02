import requests
import json
import time
import hmac, hashlib
import base64


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))

# https://bitfinex.readme.io/v1/reference#rest-auth-deposit

class bitfinex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret
        self.coin_separator = ''
        self.direct_pairs = ['BTCUSD', 'ETHBTC', 'ETHUSD', 'BTCBCH', 'BCHUSD', 'XRPUSD']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            ret = requests.get('https://api.bitfinex.com/v1/book/' + str(req['currencyPair']) +'?limit_bids=1&limit_asks=1')
            return ret.json()
        else:
            ret = requests.get('https://api.bitfinex.com/v1/' + command + '/' + '/'.join(req.values())+ '?limit_bids=1&limit_asks=1000000')
            return ret.json()

    @property
    def _nonce(self):
        """
        Returns a nonce
        Used in authentication
        """
        return str(time.time() * 1000000)

    def _sign_payload(self, payload):
        j = json.dumps(payload)
        data = base64.standard_b64encode(j.encode('utf8'))

        h = hmac.new(self.Secret.encode('utf8'), data, hashlib.sha384)
        signature = h.hexdigest()
        return {
            "X-BFX-APIKEY": self.APIKey,
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": data
        }


    def api_query_private(self, command, req={}):
        payload = {
            "request": "/v1/" + command,
            "nonce": self._nonce,
        }

        for k, v in req.items():
            payload[k] = v

        signed_payload = self._sign_payload(payload)

        ret = requests.post('https://api.bitfinex.com/v1/' + command + '/', headers=signed_payload, verify=True)
        return ret.json()


    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})


    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}
        currency_pair_list = [from_coin, to_coin]

        currency_pair = "".join(currency_pair_list)
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            a = res['asks'][0]
            price, volume = a['price'], a['amount']

            price = float(price)
            volume = float(volume)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "".join(reversed(currency_pair_list))
            res = self.returnOrderBook(currency_pair)
            b = res['bids'][0]
            price, volume = b['price'], b['amount']
            price = float(price)
            volume = float(volume)
            return {'price': float(price), 'volume': volume}


    def order_book_aggregated_top1(self, from_coin, to_coin, min_trade, cached):
        return self.order_book_top1(from_coin, to_coin)


    def get_balances(self):
        res = self.api_query_private('balances', {})

        if res is not None:
            return res
        else:
            return None


    def get_balance(self, currency):
        res = self.api_query_private('balances', {'currency': currency})

        if res is not None:
            for coin_res in res:
                if coin_res['currency'] == currency.lower():
                    return float(coin_res['amount'])
            else:
                return 0
            return res['result']['Balance']
        else:
            return None

#----------------------------------------------------------------------------------------------------------------------
# funding

    def get_lending_balance(self, currency):
        res = self.api_query_private('my_lending_balance', {'currency': currency})

        if res is not None:
            for coin_res in res:
                if coin_res['currency'] == currency.lower():
                    return float(coin_res['amount'])
            else:
                return 0
            return res['result']['Balance']
        else:
            return None


    def cancel_offer(self, offer_id):
        res = self.api_query_private('offer/cancel', {'offer_id':offer_id})

        if res is not None:
            return res
        else:
            return None


    def create_offer(self, currency, amount, rate, period):
        params  = {'currency' : currency,
                   'amount'   : amount,
                    'rate'    : rate,
                    'period'  : period,
                    'direction' : 'lend' }

        res = self.api_query_private('offer/new', params)

        if res is not None:
            return res
        else:
            return None


    def get_offers(self):
        res = self.api_query_private('offers', {})

        if res is not None:
            return res
        else:
            return None


    def get_lending_book(self, currency):
        res = self.api_query('lendbook', {'currency': currency})

        if res is not None:
            return res
        else:
            return None

# ----------------------------------------------------------------------------------------------------------------------
# marginal trading
    def create_order(self, symbol, amount, price, side, type):
        params = {
            'symbol': symbol,
            'amount': str(amount),
            'price': str(price),
            'exchange': 'bitfinex',
            'side': side,
            'type': type
        }

        '''
        type = “market” / “limit” / “stop” / “trailing-stop” / “fill-or-kill” / “exchange market” / “exchange limit” / “exchange stop” / “exchange trailing-stop” / “exchange fill-or-kill”. 
        '''
        res = self.api_query_private('order/new', params)

        if res is not None:
            return res
        else:
            return None

