from time import time, sleep, strftime, localtime
import math
import signal
from multiprocessing import Pool

from bittrex import bittrex
from config import config
from log import Log, DB

#import matplotlib.pyplot as plt


try:
    from keys import bittrex_keys
except ImportError:
    class bittrex_keys:
        api_key = ""
        api_secret = ""

def get_price(from_coin, to_coin, cached=True, aggregation_volume=None):
    if aggregation_volume is None:
        aggregation_volume = 0

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin, aggregation_volume, cached)
    return float(ob['price'])


def convert(amount_from, from_coin, to_coin, fee=config.tx, cached=True, aggregation_volume=None):
    if aggregation_volume is None:
        aggregation_volume = amount_from

    price = get_price(from_coin, to_coin, cached=cached, aggregation_volume=aggregation_volume)
    amount_to = amount_from / price * (1 - fee)

    return amount_to

def dust2coin0(dust):
    res = [
        convert(amount, from_coin=coin, to_coin=arbitrage_coins[0], cached=False) for (coin, amount)
        in dust.items() if coin != arbitrage_coins[0]]
    return res

def mark_to_ticker(dust):
    hor_count = 20
    res = [0] * hor_count
    for (coin, amount) in dust.items():
        if coin != arbitrage_coins[0]:
            price_history = exchange.get_ticket(coin, arbitrage_coins[0])
            price_history = price_history[-hor_count:]
            for i, p in enumerate(p['C'] for p in price_history):
                res[i] += amount * p

    return res

if __name__ == '__main__':


    pool = Pool(3)

    exchange = bittrex(bittrex_keys.api_key, bittrex_keys.api_secret)
    arbitrage_coins = ['USDT', 'ETH', 'XRP', 'BTC', 'NEO']
    balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))


    print(balances)
    res = mark_to_ticker(balances)
    print(res)

    while True:
        # TODO: do it once in 3-5 sec, plot it
        print(dust2coin0(balances))
        print(sum(dust2coin0(balances)))

        sleep(5)

        #https://stackoverflow.com/questions/1574088/plotting-time-in-python-with-matplotlib
        #https://stackoverflow.com/questions/11874767/real-time-plotting-in-while-loop-with-matplotlib
        #plt.ion()
        #dates = plt.dates.date2num(list_of_datetimes)
        #plt.pyplot.plot_date(dates, values)

        #https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName=USDT-BTC&tickInterval=day






