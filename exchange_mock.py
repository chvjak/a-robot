class ExchangeMock:
    def __init__(self):
        self.coin_separator = '-'
        self.direct_pairs = ['USDT-BTC', 'BTC-ETH', 'USDT-ETH', 'USDT-ZEC', 'ETH-ZEC', 'ETH-DASH', 'BTC-DASH',
                             'USDT-DASH', 'ETH-XRP', 'BTC-XRP', 'USDT-XRP', 'BTC-LTC', 'ETH-LTC', 'USDT-LTC', 'BTC-BCC',
                             'ETH-BCC', 'USDT-BCC']

        self.quotes = {}
        self.quotes['USDT-BTC'] = {'result':{'sell':[{"Quantity" : 1, "Rate" : 2001}], 'buy':[{"Quantity" : 1, "Rate" : 2000}]}}
        self.quotes['USDT-ETH'] = {'result':{'sell':[{"Quantity" : 1, "Rate" : 201}], 'buy':[{"Quantity" : 1, "Rate" : 200}]}}
        #self.quotes['BTC-ETH'] = {'result':{'sell':[{"Quantity" : 1, "Rate" : 0.11}], 'buy':[{"Quantity" : 1, "Rate" : 0.1}]}}    #Eth/btc = 1/10 if less or geater = > arbitrage
        self.quotes['BTC-ETH'] = {'result': {'sell': [{"Quantity": 1, "Rate": 0.55}], 'buy': [{"Quantity": 1, "Rate": 0.5}]}}  # Eth/btc = 1/10 if less or geater = > arbitrage

        self.order_log = {}
        self.order_mock = {}

    def returnOrderBook(self, currencyPair):
        return self.quotes[currencyPair]

    def order_book_top1(self, from_coin, to_coin, cached=True):

        currency_pair = "-".join([from_coin, to_coin])
        if currency_pair in self.direct_pairs:
            res = self.returnOrderBook(currency_pair)
            self.quotes[currency_pair] = res

            res1 = res['result']['sell'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            #return {'price': price, 'volume': volume}               # usdt => eth : usdt-eth => price in usdt, volume in eth - AGAINST expectations!
            return {'price': price, 'volume': volume * price}       # usdt => eth : usdt-eth => price in usdt, volume in usdt
        else:
            currency_pair = "-".join([to_coin, from_coin])
            res = self.returnOrderBook(currency_pair)
            self.quotes[currency_pair] = res

            res1 = res['result']['buy'][0]
            price, volume = res1['Rate'], res1['Quantity']
            price = float(price)
            #return {'price': 1.0 / price, 'volume': volume * price} # eth => btc: btc-eth => original price in btc, volume in eth => 1/price in eth, (volume in eth) * (price in btc) = NONSENSE!
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
            o_id = res["result"]["OrderUuid"]

            # could also store actual amounts for further PL calculations, also time could be useful to benchmark ordr execution time, and freqs of arb ops
            self.order_log[o_id] = {"CurrencyPair": "-".join([from_coin, to_coin])}

            return o_id
        else:
            exit()
            return ""

    def _create_order_mock(self, market, quantity, rate):
        res ={'success': True, 'result':{'OrderUuid': 'f0bc0e56-7067-46e0-b436-8fe43e2fb6ab', 'Exchange': market, 'Quantity': quantity, 'QuantityRemaining': quantity, 'Limit': rate, 'Reserved': 0.00073164, 'ReserveRemaining': 0.00073164, 'CommissionReserved': 0.0, 'CommissionReserveRemaining': 0.0, 'CommissionPaid': 0.0, 'Price': 0.0, 'PricePerUnit': None, 'Opened': '2017-08-03T11:06:44.95', 'Closed': None, 'IsOpen': True}}
        return res

    def buy_limit(self, market, quantity, rate):
        order_response = self._create_order_mock(market, quantity, rate)
        o_id = order_response["result"]['OrderUuid']
        self.order_mock[o_id] = order_response
        return self.order_mock[o_id]

    def sell_limit(self, market, quantity, rate):
        return self.buy_limit(market, quantity, rate)

    def cancel_order(self, uuid):
        self.order_mock[uuid]["result"]['IsOpen'] = False
        return self.order_mock[uuid]

    def get_order(self, uuid):
        order = self.order_mock[uuid]
        print(order)
        return order

    def is_order_open1(self, uuid):
        order = self.get_order(uuid)
        return order["result"]["IsOpen"]

    def is_order_open(self, uuid):
        return False

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


