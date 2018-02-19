from bitfinex import bitfinex
from keys import bitfinex_keys
from trading_funcs import *
import trading_funcs

exchange = bitfinex(bitfinex_keys.api_key, bitfinex_keys.api_secret)
trading_funcs.exchange = exchange

target_coin = 'ETH'
trade_amount = 1000
profit_percent = 0.0012
loss_percent = 0.1
spread_fraction = 50.0

amount_sell = convert(trade_amount, 'USD', target_coin )
sell_price = get_price(from_coin='USD', to_coin=target_coin)


if True:
    res = exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=sell_price * 0.1, side='sell', order_type='limit', ocoorder=True, sell_price_oco=sell_price * (1 - config.tx / spread_fraction))
    print(res)
    buy_price = sell_price * (1 - config.tx / spread_fraction - config.tx - config.tx / 2.0 - profit_percent)

else:
    res = exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=sell_price, side='sell', order_type='market')
    print(res)
    buy_price = sell_price * (1 - config.tx - config.tx / 2.0 - profit_percent)


if 'id' in res.keys():
    if True:
        print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=buy_price, side='buy', order_type='limit'))
    else:
        bpo = sell_price * (1 + loss_percent)
        print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=buy_price, side='buy', order_type='limit', ocoorder=True, buy_price_oco=bpo))

'''
buy_price = 100.0
bpo = 2000.0
spo = 1000.0   # not used
print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=buy_price, side='buy', order_type='limit', ocoorder=True, buy_price_oco=bpo, sell_price_oco=spo))

sell_price = 1000.0
bpo = 2000.0    #not used
spo = 100.0
print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=sell_price, side='sell', order_type='limit', ocoorder=True, buy_price_oco=bpo, sell_price_oco=spo))
'''