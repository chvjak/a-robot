from time import time, sleep, strftime, localtime

from gdax import gdax
from bitfinex import bitfinex
from poloniex import poloniex
from btce import btce
from gemini import gemini
from bittrex import bittrex
from exchange_mock import ExchangeMock
from kraken import kraken

AC2 = "NEO"
class config:
        timeout   = 2
        trade_vol = 3                #2DO: should around 400 usd,  to have arbitrages on substatial amounts, possibly with aggregation, to satisfy  trade_vol_percent_min
        test_vol  = 200
        tx        = 0.0025
        eps       = 0.000000001
        max_loss  = -0.1
        cooldown_time = 30
        min_trade_btc = 0.0005
        trade_vol_percent_min = 5
        ob_max_age_delta = 3
'''
New class candidates:
    
    class position:
        
        volume
        coin
        
        convert(to_coin)
        
    class trading:
        exchange
        arbitrage_coins
        
        get_relevant_pairs()
        try_buy() #used by do_arbitrage
        get_vol(from_coin, to_coin)
        get_price(from_coin, to_coin)

        do_arbitrage()
        test_arbitrage()
        
        
'''
def two_trans():
    # 2-transactions research
    p01 = get_price(from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1])
    p02 = get_price(from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2])
    p12 = get_price(from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2])

    r12 = p01 / p02

    p10 = get_price(from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0])
    p20 = get_price(from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0])
    p21 = get_price(from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1])

    r21 = p10 / p20

    # r12 vs p12 and r21 vs p21 should signal about cheap/expensive coins on USD or 'cross' markets

    print("r12 = %f, p21 = %f " % (r12, p21))
    print("r21 = %f, p12 = %f " % (r21, p12))


def get_relevant_pairs(exchange, arbitrage_coins):
    res = []
    pairs = []
    for p1 in arbitrage_coins:
        for p2 in arbitrage_coins:
            if p1 != p2:
                pairs += [exchange.coin_separator.join([p1, p2])]

    res = [p for p in pairs if p in exchange.direct_pairs]

    return res


def get_min_trade(trade_coin):
    if trade_coin == "BTC":
        return config.min_trade_btc
    else:
        return convert1(config.min_trade_btc, from_coin="BTC", to_coin=trade_coin, fee=0)


def try_buy(amount_to, from_coin, to_coin):
    print("Trying to buy %f of %s for %s." % (amount_to, to_coin, from_coin))
    ARBITRAGE_PRICE = get_price(from_coin, to_coin)

    print("ARBITRAGE_PRICE = %f %s." % (ARBITRAGE_PRICE, from_coin))
    order = exchange.create_order(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)

    if order == -1:
        print("Could not create order.")
        exit()

    time2 = time1 = time()
    while time2 - time1 < config.timeout and exchange.is_order_open(order):
        print('.',end='')
        time2 = time()

    print()
    if exchange.is_order_open(order):
        exchange.cancel_order(order)

        print("Order for %10.10f %s was not executed during timeout." % (amount_to, to_coin))
        remaining_amount_to = exchange.order_remaining_amount(order)

        print("Remaining amount is %10.10f" % remaining_amount_to)
        if (amount_to - remaining_amount_to) > config.eps:
            print("The order was partially executed. Actual result amount is %f %s " % (amount_to - remaining_amount_to, to_coin))
            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE
            print("remaining_amount_from = %f, PRICE = %f" % (remaining_amount_from, ARBITRAGE_PRICE))
            # should remaining_amount_from be used in market_sell?

        actual_amount_to = amount_to - remaining_amount_to

        if from_coin != "USDT" and remaining_amount_to > 0:

            # if BTC->BCC conversion fails, BTC->USDT conversion follows and reserved tx fee was not spent
            # BUT if it was BCC->BTC transaction the source of BTC then there is no unused fee
            # 2FIX: better fix needed. E.g get to ACTUAL from_amounts, OR use info from order, implies caching of order info
            if from_coin == "BTC" and to_coin == AC2:
                print("Increasing BTC amount to reflect unuset comission")
                print("before increse = %f" % remaining_amount_to)
                remaining_amount_to *= (1 + config.tx)
                print("after increse = %f" % remaining_amount_to)

            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE                        # use 'sell price' to recover remaining unsold amount, actually it is availble as order property
            usd_amount = market_sell(remaining_amount_from, from_coin, to_coin = "USDT")

            if to_coin == "USDT":
                actual_amount_to += usd_amount
                usd_amount = 0
        else:
            usd_amount = 0

    else:
        print("Order for %10.10f %s was executed " % (amount_to, to_coin))
        actual_amount_to = amount_to
        usd_amount = 0

        # 2DO: fee is always charged in QUOTATION currency
        if to_coin != AC2:
            actual_amount_to *= (1 - config.tx)

    print("Actual bought amount = %10.10f %s" % (actual_amount_to, to_coin))

    return actual_amount_to, usd_amount

def market_sell(amount_from, from_coin, to_coin):
    amount_to = convert(amount_from, from_coin, to_coin, fee=0)
    remaining_amount_from = amount_from
    res = 0

    rep_count = 0
    while amount_to > get_min_trade(to_coin):
        PRICE = get_price(from_coin, to_coin, cached=False)
        amount_to = remaining_amount_from / PRICE
        print("remaining_amount_from = %f, PRICE = %f" % (remaining_amount_from, PRICE))
        print("UPDATED amount_to = %10.10f" % (amount_to))

        order = exchange.create_order(from_coin, to_coin, amount_to, PRICE)
        print("Trying to buy %f of %s for %f %s (price = %f %s)." % (amount_to, to_coin, amount_from, from_coin, PRICE, from_coin))

        if order == -1:
            remaining_amount_from = amount_to * PRICE
            print("RECOVERED amount_from = %10.10f" % (remaining_amount_from))

            # HACK - indefinite situation, need to stop and investigate
            if rep_count <= 3:
                rep_count += 1
                continue
            else:
                exit()

        time2 = time1 = time()
        while time2 - time1 < config.timeout and exchange.is_order_open(order):
            print('.', end='')
            time2 = time()
        print()

        if exchange.is_order_open(order):
            exchange.cancel_order(order)
            print("Order for %f %s was not executed during timeout." % (amount_to, to_coin))

            remaining_amount_to = exchange.order_remaining_amount(order)
            print("Remaining amount is %10.10f" % remaining_amount_to)

            if (amount_to - remaining_amount_to) > config.eps:
                print("The order was partially executed. Actual result amount is %10.10f %s " % (amount_to - remaining_amount_to, to_coin))
                res += amount_to - remaining_amount_to

                remaining_amount_from = remaining_amount_to * PRICE
                amount_to = remaining_amount_to

        else:
            res += amount_to
            amount_to = 0

    print("Actual bought amount = %10.10f %s" % (res, to_coin))
    return res


def get_1price(from_coin, to_coin, cached = True):

    ob = exchange.order_book_top1(from_coin, to_coin, cached)
    return float(ob['price'])


def get_1vol(from_coin, to_coin):

    ob = exchange.order_book_top1(from_coin, to_coin)
    return ob['volume']

def convert1(amount_from, from_coin, to_coin, fee = config.tx, cached = True):
    price = get_1price(from_coin, to_coin, cached)

    amount_to = amount_from / price * (1 - fee)

    #print("%f %s in %s is %f" % (amount_from, from_coin, to_coin, amount_to))

    return amount_to

def get_vol(from_coin, to_coin, aggregation_volume = None):
    if aggregation_volume is None:
        aggregation_volume = get_min_trade(from_coin)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin, aggregation_volume)
    return ob['volume']


def get_price(from_coin, to_coin, cached = True, aggregation_volume = None):
    if aggregation_volume is None:
        aggregation_volume = get_min_trade(from_coin)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin,  aggregation_volume, cached)
    return float(ob['price'])

def convert(amount_from, from_coin, to_coin, fee = config.tx, cached = True):
    price = get_price(from_coin, to_coin, cached=cached, aggregation_volume=amount_from)
    amount_to = amount_from / price * (1 - fee)

    return amount_to


if __name__ == '__main__':
    from multiprocessing import Pool
    pool = Pool(3)

    #exchange = bitfinex("", "")
    #exchange = poloniex("", "")
    #exchange = btce("", "")
    #exchange = gemini("", "")
    #exchange = kraken("", "")
    #exchange = gdax("", "")
    exchange = bittrex("", "")
    #exchange = ExchangeMock()

    #kraken
    #arbitrage_coins = ['USD', 'ETH', 'XBT']

    #btce, #bitfinex
    #arbitrage_coins = ['usd', 'eth', 'btc']

    #bittrex, poloniex
    arbitrage_coins = ['USDT', AC2, 'BTC']


    max_profit = 0
    max_pp = 0
    sum_profit = 0
    ok_arb_count = 0
    failed_arb_count = 0
    too_small_count = 0
    arb_count = 0
    max_aa = 0
    time_prev_arb = 0

    min_arb_execution_time = 100
    max_arb_execution_time = 0
    sum_arb_execution_time = 0

    print(strftime("%H:%M:%S", localtime()))
    while 1:
        pairs = get_relevant_pairs(exchange, arbitrage_coins)
        exchange.quotes = dict(zip(pairs, pool.map(exchange.returnOrderBook, pairs)))

        if any(x is None for x in exchange.quotes.values()):
            print("Cooling down")
            sleep(config.cooldown_time)
            continue
        else:
            #print('TOTAL OB LENGTH = %d' % sum([len(x.__repr__()) for x in exchange.quotes.values()]))
            time1 = time()
            if any(abs(x['time'] - time1) > config.ob_max_age_delta for x in exchange.quotes.values()):
                print('|', end='', flush=True)
                continue
            else:
                print('.', end='', flush=True)

        arb1 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0]) - config.test_vol
        arb2 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0]) - config.test_vol


        if arb1 > 0 or arb2 > 0:
            print()
            time_prev_arb = time()

            arb_count += 1
            print(strftime("%H:%M:%S", localtime()))
            print("ARBITRAGE DETECTED %d" % (arb_count ))

            if arb2 > arb1:
                arbitrage_coins[1], arbitrage_coins[2] = arbitrage_coins[2], arbitrage_coins[1]


            # get available volume V from_coin order book
            av0 = config.test_vol
            av1 = convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1], fee=0)
            av2 = convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2], fee=0)
            amount_onsale_from0_to1_as0 = get_vol(from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], aggregation_volume=av0)

            amount_onsale_from1_to2_as1 = get_vol(from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], aggregation_volume=av1)
            amount_onsale_from1_to2_as0 = convert(amount_onsale_from1_to2_as1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0], fee = 0)

            amount_onsale_from2_to0_as2 = get_vol(from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0], aggregation_volume=av2)
            amount_onsale_from2_to0_as0 = convert(amount_onsale_from2_to0_as2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0], fee = 0)

            amount_to_spend0 = min(amount_onsale_from0_to1_as0 , amount_onsale_from1_to2_as0 , amount_onsale_from2_to0_as0, config.trade_vol)         # ARBITRAGE AMOUNT
            amount_to_spend_ul0 = min(amount_onsale_from0_to1_as0, amount_onsale_from1_to2_as0, amount_onsale_from2_to0_as0)

            if (config.trade_vol / amount_to_spend_ul0) * 100 < config.trade_vol_percent_min:
                amount_to_spend0 = config.trade_vol
            else:
                print("TOO SMALL: %f %%" % ((config.trade_vol / amount_to_spend_ul0) * 100))
                continue


            V1 = amount_to_spend0
            V3 = convert(convert(convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
            p = (V3 - V1)
            pp = (100 * (V3 / V1 - 1))

            max_aa = max(amount_to_spend_ul0, max_aa)
            max_profit = max(max_profit, p)
            max_pp = max(max_pp, pp)

            print("ARBITRAGE AMOUNT: %f" % V1)
            print("ARBITRAGE UL AMOUNT: %f" % amount_to_spend_ul0)
            print("MAX UL AMOUNT: %f" % max_aa)

            print("ARBITRAGE PROFIT: %f" % p)
            print("ARBITRAGE PROFIT,%%: %f %%" % pp)

            print("MAX PROFIT = %f" % max_profit)
            print("MAX PROFIT, %% = %f %%" % max_pp)

            # trade
            if True:
                amount_to_buy1 = convert(amount_to_spend0, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], fee=0)
                amount_recieved1, sink = try_buy(amount_to_buy1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
                print(strftime("%H:%M:%S", localtime()))
                if (amount_recieved1 - get_min_trade(arbitrage_coins[1])) > 0:
                    amount_to_buy2 = convert(amount_recieved1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], fee=0)
                    amount_recieved2, usd_amount = try_buy(amount_to_buy2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                    print(strftime("%H:%M:%S", localtime()))
                    if (amount_recieved2 - get_min_trade(arbitrage_coins[2])) > 0:
                        #final_amount = market_sell(amount_recieved2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

                        amount_to_buy0 = convert(amount_recieved2, from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0], fee=0)
                        final_amount, sink = try_buy(amount_to_buy0, from_coin=arbitrage_coins[2],  to_coin=arbitrage_coins[0])

                        profit = final_amount + usd_amount - amount_to_spend0 * (1 + config.tx)
                        sum_profit += profit

                        if profit > 0:
                            print("+++PROFIT = %f" % (profit))
                            ok_arb_count += 1
                        else:
                            print("---LOSS = %f" % (profit))
                            failed_arb_count += 1


                    else:
                        #LOSS
                        loss = usd_amount - amount_to_spend0 * (1 + config.tx)
                        sum_profit += loss
                        print("---LOSS = %f" % (loss))
                        failed_arb_count += 1

                    arb_execution_time = time() - time_prev_arb

                    sum_arb_execution_time += arb_execution_time

                    min_arb_execution_time = min(min_arb_execution_time, arb_execution_time )
                    max_arb_execution_time = max(max_arb_execution_time, arb_execution_time)

                    print(strftime("%H:%M:%S", localtime()))
                    print("***SUM PROFIT/LOSS = %f" % (sum_profit))
                    print("P:%d L:%d" % (ok_arb_count, failed_arb_count))
                    print("ARBITRAGE TOOK %f sec" % (arb_execution_time))
                    print("EXECUTION TIME: AVG %f sec, MIN %f sec, MAX %f sec" % (sum_arb_execution_time/(ok_arb_count + failed_arb_count), min_arb_execution_time, max_arb_execution_time))

                    print("")

                    if sum_profit < config.max_loss:
                        break


'''
+-! 1. Aggregation should help against TOO SMALL
    1a TOO SMALL vs trade_amount NOT vs min_trade
    1b With price grows of BTC $2 might become 'dust' soon
    

!2. FAILED ARB could be fixed by simultaneous orders with some position in arb_coins
    Seems doesn't make much sense since it increases exposure to market <= requires open positions for indefinite time

++- 3. 2FIX - false fee assumption during USDT-BTC trade
++- 3a. 2FIX - INSUFFICIENT FUNDS on market_sell
    3b. 2FIX - INSUFFICIENT FUNDS on try_buy, see log3
    3c. 2FIX - order fill in the moment of order cancel


!4. 2DO: command line iface for research, i.e.: start.py EXCHANGE COIN1 COIN2 COIN3

5. 2DO: .csv or other output fmt for further analysis - freq of arb, size of arb(avg, max), freq of trades
    - may be db is better due to possible simultaneous run of scripts. this might imply use of MPQUEUE for logging, + logging thread which outs data into db

+-6. reduce verbosity of logs - too_smalls, order dumps - could be hidden

+-7. 2DO: fix crash on 'no response' from exchange

8. SPEEDUP: avoid exchange roundtrip for remainig amount of order

+-9. 2FIX: 300 sec waits for order execution. This might be long r4esponse from exchange

import requests
import eventlet
eventlet.monkey_patch()

with eventlet.Timeout(10):
    requests.get("http://ipv4.download.thinkbroadband.com/1GB.zip", verify=False)
    

10. 2DO: Deal with HTTP timeouts/delays:
    - on order create/is open - most dangerous. If First order took too long => close position
    - if is_open timedout => stop(?)
    - probably cooldown in this cases 
'''