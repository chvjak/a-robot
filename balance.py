from time import time, sleep, strftime, localtime
import math
import signal
from multiprocessing.dummy import Pool
#from multiprocessing import Pool

from bittrex import bittrex
from bitfinex import bitfinex
from config import config
from log import Log, DB

import matplotlib.pyplot as plt
import matplotlib as _matplotlib


try:
    from keys import bittrex_keys
    from keys import bitfinex_keys
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
        convert(float(amount), from_coin=coin, to_coin=arbitrage_coins[0], cached=False) for (coin, amount)
        in dust.items() if coin != arbitrage_coins[0]]
    return res

def mark_to_ticker(dust):
    # {'O': 320.0, 'H': 321.88999996, 'L': 317.0, 'C': 318.59999983, 'V': 341.62961994, 'T': '2017-08-23T19:00:00', 'BV': 109130.19935431}
    hour_count = 20
    res = [0] * hour_count
    for (coin, amount) in dust.items():
        if coin != arbitrage_coins[0]:
            price_history = exchange.get_ticket(coin, arbitrage_coins[0], interval='hour')
            #price_history = exchange.get_ticket(coin, arbitrage_coins[0], interval='day')
            price_history = price_history[-hour_count:]
            for i, p in enumerate(p['C'] for p in price_history):
                res[i] += 0 if amount is None else amount * p


    #plt.plot_date(_matplotlib.dates.date2num([p['T'] for p in price_history]), res)
    dates = [x for x in range(hour_count)]
    plt.plot(dates, res)
    plt.show()

    return res

if __name__ == '__main__':


    pool = Pool(3)

    exchange = bittrex(bittrex_keys.api_key, bittrex_keys.api_secret)
    #exchange = bitfinex(bitfinex_keys.api_key, bitfinex_keys.api_secret)

    arbitrage_coins = ['BCC', 'BTC', 'ADA', 'NEO', 'OMG', 'USDT']
    balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))
    #b1 = exchange.get_balance('BCH')
    #b2 = exchange.get_balance('BTC')

    #b1 = convert(b1 , 'BCH', 'USD')
    #b2 = convert(b2, 'BTC', 'USD')

    print(balances)
    #print(dust2coin0(balances))
    print(sum(dust2coin0(balances)))

    exit()

    while True:
        res = mark_to_ticker(balances)
        print(res)

        # TODO: do it once in 3-5 sec, plot it

        sleep(5)

        #https://stackoverflow.com/questions/1574088/plotting-time-in-python-with-matplotlib
        #https://stackoverflow.com/questions/11874767/real-time-plotting-in-while-loop-with-matplotlib
        #plt.ion()
        #dates = plt.dates.date2num(list_of_datetimes)
        #plt.pyplot.plot_date(dates, values)

        #https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName=USDT-BTC&tickInterval=day






