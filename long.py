from bitfinex import bitfinex
from keys import bitfinex_keys
from config import config
from trading_funcs import *
import trading_funcs

exchange = bitfinex(bitfinex_keys.api_key, bitfinex_keys.api_secret)
trading_funcs.exchange = exchange

target_coin = 'ETH'
trade_amount = 100
profit_percent = 0.0025

amount_buy = convert(trade_amount, 'USD', target_coin )
buy_price = get_price(from_coin='USD', to_coin=target_coin)

sell_price = buy_price * (1 + 2 * config.tx + profit_percent)

exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=buy_price, side='buy', type='market')
exchange.create_order(symbol=target_coin + 'USD', amount=amount_buy, price=sell_price, side='sell', type='limit')      # or oco?
