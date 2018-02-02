from bitfinex import bitfinex
from keys import bitfinex_keys
from config import config
from trading_funcs import *
import trading_funcs

exchange = bitfinex(bitfinex_keys.api_key, bitfinex_keys.api_secret)
trading_funcs.exchange = exchange

target_coin = 'ETH'
trade_amount = 1800

amount_sell = convert(trade_amount, 'USD', target_coin )
sell_price = get_price(from_coin='USD', to_coin=target_coin)

buy_price = sell_price * (1 - 2 * config.tx - 0.0025)

exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=sell_price, side='sell', type='market')
exchange.create_order(symbol=target_coin + 'USD', amount=amount_sell, price=buy_price, side='buy', type='limit')      # or oco?
