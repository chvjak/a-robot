import requests
import json
import time
import hmac, hashlib
import base64


class bitfinex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret
        self.coin_separator = ''
        self.direct_pairs = ['BTCUSD', 'ETHBTC', 'ETHUSD', 'BTCBCH', 'BCHUSD']

    def api_query(self, command, req={}):
        ret = requests.get('https://api.bitfinex.com/v1/' + command + '/' + '/'.join(
            req.values()) + '?limit_bids=1&limit_asks=1000000')
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

    def cancel_offer(self, offer_id):
        res = self.api_query_private('offer/cancel', {'offer_id': offer_id})

        if res is not None:
            return res
        else:
            return None

    def create_offer(self, currency, amount, rate, period):
        params = {'currency': currency,
                  'amount': str(amount),
                  'rate': str(rate),
                  'period': period,
                  'direction': 'lend'}

        print(params)
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


class bitfinex_lender_keys:
    api_key = ""
    api_secret = ""


def lambda_handler(event, context):
    exchange = bitfinex(bitfinex_lender_keys.api_key, bitfinex_lender_keys.api_secret)

    # check for existing offers - cancel them
    offers = exchange.get_offers()
    for o in offers:
        exchange.cancel_offer(o['id'])

    # get available lending balance for given coin
    balances = exchange.get_balances()
    # balances = [{'type': 'deposit', 'currency': 'eth', 'amount': '2.00003762', 'available': '200'}]

    # offer funding at the price of small_fraction of all funds
    small_fraction = 0.005
    small_fraction_override = {'eth': 0.0025}

    for b in balances:

        if b['currency'] in small_fraction_override.keys():
            sf = small_fraction_override[b['currency']]
        else:
            sf = small_fraction

        if b['type'] == 'deposit':
            if float(b['available']) > 0.001:
                if b['currency'] == 'none':
                    continue
                print(b)

                book = exchange.get_lending_book(b['currency'])

                if len(book['asks']):
                    total_offers = 0
                    for a in book['asks']:
                        total_offers += float(a['amount'])

                    small_fraction_sum = 0
                    rate = book['asks'][0]['rate']
                    for a in book['asks']:
                        small_fraction_sum += float(a['amount'])
                        if small_fraction_sum > total_offers * sf:
                            # rate is per annum
                            rate = float(a['rate'])
                            break

                    print('total offered ', total_offers)
                    print('{}% sum is {}'.format(sf, small_fraction_sum))
                    print('{}% rate is {} per year, {} pr day'.format(sf, rate, rate / 365.0))

                    amount = float(b['available'])

                    if b['currency'] == 'usd':
                        # rate = book['asks'][0]['rate']
                        if amount > 120:
                            amount = 60

                    # offer all balances at the 'small fraction' rate
                    exchange.create_offer(b['currency'], amount, rate, 2)
