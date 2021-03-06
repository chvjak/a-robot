import requests




class btce:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

        self.coin_separator = '_'
        self.direct_pairs = ['btc_usd', 'eth_btc', 'eth_usd']


    def api_query(self, command, req={}):

        if (command == "returnOrderBook"):

            ret = requests.get('https://btc-e.com/api/3/depth/' + str(req['currencyPair']) + '?limit=1')
            return ret.json()
        else:
            return ""
    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def returnOrderBookCached(self, currencyPair):
        return self.quotes[currencyPair]


    def order_book_top1(self, from_coin, to_coin):
        # {'asks': [['2529.04989980', 100]], 'bids': [['2529.04989980', 200]]}
        currency_pair_list = [x.lower() for x in (from_coin, to_coin)]

        currency_pair = "_".join(currency_pair_list)
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBookCached(currency_pair)
            price, volume = res[currency_pair]['bids'][0]
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "_".join(reversed(currency_pair_list))
            res = self.returnOrderBookCached(currency_pair)
            price, volume = res[currency_pair]['asks'][0]
            price = float(price)
            return {'price': float(price), 'volume': volume}

    def order_book_top10(self, from_coin, to_coin):
        # {'asks': [['2530.04', 100]], 'bids': [['2529.04', 200]]}
        currency_pair_list = [x.lower() for x in (from_coin, to_coin)]

        currency_pair = "_".join(currency_pair_list)
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            price, volume = res[currency_pair]['bids'][0]
            price = float(price)
            return {'price': 1.0 / price, 'volume': volume * price}

        else:
            currency_pair = "_".join(reversed(currency_pair_list))
            res = self.returnOrderBook(currency_pair)
            price, volume = res[currency_pair]['asks'][0]
            price = float(price)
            return {'price': float(price), 'volume': volume}


