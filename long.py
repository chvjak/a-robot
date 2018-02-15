from bitfinex import bitfinex
from keys import bitfinex_keys
from trading_funcs import *
import trading_funcs

exchange = bitfinex(bitfinex_keys.api_key, bitfinex_keys.api_secret)
trading_funcs.exchange = exchange

target_coin = 'eth'
trade_amount = 1000
profit_percent = 0.00125
loss_percent = 0.1
spread_fraction = 50.0

amount_buy = convert(trade_amount, 'USD', target_coin )
buy_price = get_price(from_coin='USD', to_coin=target_coin)

print('buy_price =', buy_price )

if True:
    res = exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=buy_price * 0.1, side='buy', order_type='limit', ocoorder=True, buy_price_oco=buy_price * (1 + config.tx / spread_fraction))
    print(res)
    sell_price = buy_price * (1 + config.tx / spread_fraction + config.tx / 2.0 + config.tx / 2.0 + profit_percent)
else:
    res = exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=buy_price, side='buy', order_type='market')
    print(res)
    sell_price = buy_price * (1 + config.tx + config.tx / 2.0 + profit_percent)


if 'id' in res.keys():
    if True:
        '''
        {'message': 'Cannot evaluate your available balance, please try agian'}
        {'id': 8037419156, 'cid': 48335225441, 'cid_date': '2018-02-07', 'gid': None, 'symbol': 'ethusd', 'exchange': 'bitfinex', 'price': '851.31', 'avg_execution_price': '0.0', 'side': 'sell', 'type': 'limit', 'timestamp': '1518009935.245941163', 'is_live': True, 'is_cancelled': False, 'is_hidden': True, 'oco_order': None, 'was_forced': False, 'original_amount': '1.1790362', 'remaining_amount': '1.1790362', 'executed_amount': '0.0', 'src': 'api', 'order_id': 8037419156}
        '''
        print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=sell_price, side='sell', order_type='limit'))
    else:
        spo = buy_price * (1 - loss_percent)
        print(exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=sell_price, side='sell', order_type='limit', ocoorder=True, sell_price_oco=spo))

