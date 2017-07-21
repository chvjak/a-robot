import requests


class kraken:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

        self.direct_pairs = ['XBTUSD', 'ETHXBT', 'ETHUSD']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):
            ret = requests.get('https://api.kraken.com/0/public/Depth?pair=' + str(req['currencyPair']))
            return ret.json()
        else:
            return ""

    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}

        currency_pair = "".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            key, res1 = res['result'].popitem()

            price, volume, sink = res1['asks'][0]
            price = float(price)
            volume = float(volume)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "".join([to_coin, from_coin])
            res = self.returnOrderBook(currency_pair)
            key, res1 = res['result'].popitem()

            price, volume, sink = res1['bids'][0]
            price = float(price)
            volume = float(volume )
            return {'price': float(price), 'volume': volume}


