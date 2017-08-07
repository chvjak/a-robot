from time import time

from gdax import gdax
from bitfinex import bitfinex
from poloniex import poloniex
from btce import btce
from gemini import gemini
from bittrex import bittrex
from exchange_mock import ExchangeMock
from kraken import kraken

class config:
        timeout   = 2
        trade_vol = 2
        test_vol  = 2
        tx        = 0.0025
        eps       = 0.000001
        max_loss  = -0.1
        cooldown_time = 30
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

def get_relevant_pairs(exchange, arbitrage_coins):
    res = []
    pairs = []
    for p1 in arbitrage_coins:
        for p2 in arbitrage_coins:
            if p1 != p2:
                pairs += [exchange.coin_separator.join([p1, p2])]

    res = [p for p in pairs if p in exchange.direct_pairs]

    return res

def try_buy(amount_to, from_coin, to_coin):
    '''

    :param amount_to: amount of coint to buy
    :param to_coin:
    :return: create an order to_coin spend 'amount_from' of 'from_coin' currency

    # it is possible to wait until aribitrage oportunity exists and not predefined time span
    # if only partial sale succeded it is possible to continue arbitrage change and sale unfulfilled amount with loss


buy
Places a limit buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number. Sample output:

{"orderNumber":31226040,"resultingTrades":[{"amount":"338.8732","date":"2014-10-18 23:03:21","rate":"0.00000173","total":"0.00058625","tradeID":"16164","type":"buy"}]}

You may optionally set "fillOrKill", "immediateOrCancel", "postOnly" to 1.
 A fill-or-kill order will either fill in its entirety or be completely aborted.
 An immediate-or-cancel order can be partially or completely filled, but any portion of the order that cannot be filled immediately will be canceled rather than left on the order book.
 A post-only order will only be placed if no portion of it fills immediately;
 this guarantees you will never pay the taker fee on any part of the order that fills.

    '''


    ARBITRAGE_PRICE = get_price(from_coin, to_coin)

    print("Trying to buy %f of %s for %s (price = %f %s)." % (amount_to, to_coin, from_coin, ARBITRAGE_PRICE, from_coin))
    order = exchange.create_order(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)

    time2 = time1 = time()
    while time2 - time1 < config.timeout and exchange.is_order_open(order):
        time2 = time()

    if exchange.is_order_open(order):
        print("Order for %f %s was not executed during timeout." % (amount_to, to_coin))
        remaining_amount_to = exchange.order_remaining_amount(order)

        print("Remaining amount is %f" % remaining_amount_to)
        exchange.cancel_order(order)

        actual_amount_to = amount_to - remaining_amount_to

        if from_coin != "USDT" and remaining_amount_to > 0:

            # if BTC->BCC conversion fails, BTC->USDT conversion follows and reserved tx fee was not spent
            # 2FIX: better fix needed
            if from_coin == "BTC":
                remaining_amount_to *= (1 + config.tx)

            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE                        # use 'sell price' to recover remaining unsold amount, actually it is availble as order property
            usd_amount = market_sell(remaining_amount_from, from_coin, to_coin = "USDT")

            if to_coin == "USDT":
                actual_amount_to += usd_amount
                usd_amount = 0
        else:
            usd_amount = 0

    else:
        print("Order for %f %s was executed " % (amount_to, to_coin))
        actual_amount_to = amount_to
        usd_amount = 0

        # 2DO: fee is always charged in QUOTATION currency
        if to_coin != "BCC":
            actual_amount_to *= (1 - config.tx)

    print("Actual bought amount = %f %s" % (actual_amount_to, to_coin))

    return actual_amount_to, usd_amount

def market_sell(amount_from, from_coin, to_coin):
    amount_to = convert(amount_from, from_coin, to_coin, fee=0, cached=False)  # With updated price (smaller sell price) amount_to corresponds to smaller amount of to_coint then previously
    res = 0
    while amount_to > 0:
        PRICE = get_price(from_coin, to_coin, cached=False)                    # get sell price

        print("Trying to buy %f of %s for %f %s (price = %f %s)." % (amount_to, to_coin, amount_from, from_coin,  PRICE, from_coin))
        order = exchange.create_order(from_coin, to_coin, amount_to, PRICE)    # sell price is used to crete the order

        if order == -1:
            amount_from = amount_to * PRICE         # in case it's not the first iteration - calculate residual amount_from
            amount_to = convert(amount_from, from_coin, to_coin, fee=0, cached=False)

            print("RECOVERED amount_from = %f" % (amount_from))
            print("UPDATED amount_to = %f" % (amount_to))

            continue
            #exit()

        time2 = time1 = time()
        while time2 - time1 < config.timeout and exchange.is_order_open(order):
            time2 = time()

        if exchange.is_order_open(order):
            print("Order for %f %s was not executed during timeout." % (amount_to, to_coin))
            remaining_amount_to = exchange.order_remaining_amount(order)
            print("Remaining amount is %f" % remaining_amount_to)
            exchange.cancel_order(order)

            if amount_to != remaining_amount_to:
                print("The order was partually executed. Actual result amount is %f %s " % (amount_to - remaining_amount_to, to_coin))
                res += amount_to - remaining_amount_to

                # remaining_amount_from is lost and not updated in the loop
                # HACK: better to change order_remaining_amount to return in from_coin(?)
                remaining_amount_from = remaining_amount_to * PRICE
                amount_to = convert(remaining_amount_from , from_coin, to_coin, fee=0, cached=False)

                # WRONG:
                #amount_to = remaining_amount_to

        else:
            res += amount_to
            amount_to = 0

    print("Actual bought amount = %f %s" % (res, to_coin))
    return res


def get_price(from_coin, to_coin, cached = True):
    '''
    :param from_coin:
    :param to_coin:
    :return: volume of order in the order book for sale of 'from_coin' currency to_coin 'to_coin' currency

    possibly agregate several orders if arbitrage still exists
    '''

    # ob[i] = {volume: 100; price: 55.56}
    # ob is sorted by price, ascending

    ob = exchange.order_book_top1(from_coin, to_coin, cached)
    return float(ob['price'])


def get_vol(from_coin, to_coin):
    '''
    :param from_coin:
    :param to_coin:
    :return: volume of order in the order book for sale of 'from_coin' currency to_coin 'to_coin' currency

    possibly agregate several orders if arbitrage still exists
    '''

    # ob[i] = {volume: 100; price: 55.56}
    # ob is sorted by price, ascending

    ob = exchange.order_book_top1(from_coin, to_coin)
    return ob['volume']

def convert(amount_from, from_coin, to_coin, fee = config.tx, cached = True):
    '''
    :param amount_from:
    :param to_coin:
    :return: amount of 'to_coin' currency if traded 'amount_from' amount of 'from_coin' currency considering current prices and tx fees
    '''
    price = get_price(from_coin, to_coin, cached)

    amount_to = amount_from / price * (1 - fee)

    #print("%f %s in %s is %f" % (amount_from, from_coin, to_coin, amount_to))

    return amount_to

def get_avol(from_coin, to_coin):
    if to_coin == "BTC":
        min_trade = 0.0005
    else:
        min_trade = convert(0.0005, from_coin="BTC", to_coin=to_coin, fee=0)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin, min_trade)
    return ob['volume']


def get_aprice(from_coin, to_coin):
    if to_coin == "BTC":
        min_trade = 0.0005
    else:
        min_trade = convert(0.0005, from_coin="BTC", to_coin=to_coin, fee=0)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin, min_trade)
    return float(ob['price'])

def aconvert(amount_from, from_coin, to_coin, fee = config.tx, cached = True):
    '''
    AGGREGATED convert
    '''
    price = get_aprice(from_coin, to_coin)
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
    exchange = bittrex("f1a45e061d5743c3817d02e522cc5203", "e4c6934899d84140a90bf2981c0d9b99")
    #exchange = ExchangeMock()

    #kraken
    #arbitrage_coins = ['USD', 'ETH', 'XBT']

    #btce, #bitfinex
    #arbitrage_coins = ['usd', 'eth', 'btc']

    #bittrex, poloniex
    #arbitrage_coins = ['USDT', 'ETH', 'BTC']
    arbitrage_coins = ['USDT', 'BCC', 'BTC']
    #arbitrage_coins = ['USDT', 'BCC', 'ETH']

    #arbitrage_coins = ['BTC', 'LTC', 'ETH']
    #arbitrage_coins = ['USDT', 'LTC', 'ETH']
    #arbitrage_coins = ['USDT', 'ZEC', 'ETH']
    #arbitrage_coins = ['USDT', 'ZEC', 'BTC']
    #arbitrage_coins = ['USDT', 'ETH', 'DASH']
    #arbitrage_coins = ['USDT', 'BTC', 'DASH']
    #arbitrage_coins = ['USDT', 'BTC', 'XRP']
    #arbitrage_coins = ['USDT', 'ETH', 'XRP']

    #2DO: BTC and its crosses are needed to get minimal trade amount




    max_profit = 0
    max_pp = 0
    sum_profit = 0
    ok_arb_count = 0
    failed_arb_count = 0
    too_small_count = 0
    arb_count = 0
    max_aa = 0
    while 1:
        pairs = get_relevant_pairs(exchange, arbitrage_coins)
        exchange.quotes = dict(zip(pairs, pool.map(exchange.returnOrderBook, pairs)))

        if any(x is None for x in exchange.quotes.values()):
            time.sleep(config.cooldown_time)
            continue


        arb1 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0]) - config.test_vol
        arb2 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0]) - config.test_vol

        p01 = get_price(from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1])
        p02 = get_price(from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2])
        p12 = get_price(from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2])

        r12 = p01 / p02

        p10 = get_price(from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0])
        p20 = get_price(from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0])
        p21 = get_price(from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1])

        r21 = p10 / p20

        # r12 vs p12 and r21 vs p21 should signal about cheap/expensive coins on USD or 'cross' markets

        if arb1 > 0 or arb2 > 0:
            arb_count += 1
            print("ARBITRAGE DETECTED %d" % (arb_count ))

            print(" r12 = %f, p21 = %f " % (r12, p21))
            print(" r21 = %f, p12 = %f " % (r21, p12))

            if arb2 > arb1:
                arbitrage_coins[1], arbitrage_coins[2] = arbitrage_coins[2], arbitrage_coins[1]


            # get available volume V from_coin order book
            amount_onsale_from0_to1_as0 = get_vol(from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])

            amount_onsale_from1_to2_as1 = get_vol(from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
            amount_onsale_from1_to2_as0 = convert(amount_onsale_from1_to2_as1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0], fee = 0)

            amount_onsale_from2_to0_as2 = get_vol(from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
            amount_onsale_from2_to0_as0 = convert(amount_onsale_from2_to0_as2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0], fee = 0)

            # 2CHECK if no mess in buy/sell
            amount_to_spend0 = min(amount_onsale_from0_to1_as0 , amount_onsale_from1_to2_as0 , amount_onsale_from2_to0_as0, config.trade_vol)         # ARBITRAGE AMOUNT
            amount_to_spend_ul0 = min(amount_onsale_from0_to1_as0, amount_onsale_from1_to2_as0, amount_onsale_from2_to0_as0)


            # probing code
            if True:
                V1 = amount_to_spend0
                print("ARBITRAGE AMOUNT: %f" % V1)

                max_aa = max(amount_to_spend_ul0, max_aa)
                print("ARBITRAGE UL AMOUNT: %f" % amount_to_spend_ul0)
                print("MAX UL AMOUNT: %f" % max_aa)

                '''
                            All trades submitted must be .00050000 BTC in value or greater.  Quantity * Price must be greater than .00050000 BTC.
                '''

                min_trade = convert(0.0005, from_coin="BTC", to_coin=arbitrage_coins[0], fee=0)
                if amount_to_spend0 < min_trade:
                    too_small_count += 1
                    print("TOO SMALL %d" % (too_small_count))

                    arb1 = aconvert(aconvert(aconvert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1]),from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0]) - config.test_vol
                    arb2 = aconvert(aconvert(aconvert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0]) - config.test_vol

                    print("PROFIT WITH AGGREGATION %f or %f" % (arb1, arb2))
                    if arb1 > 0 or arb2 > 0:
                        print("AGGREGATION HELPS")

                    continue



                V3 = convert(convert(convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
                p = (V3 - V1)
                pp = (100 * (V3 / V1 - 1))

                print("ARBITRAGE PROFIT: %f" % p)
                print("ARBITRAGE PROFIT,%%: %f %%" % pp)

                max_profit = max(max_profit, p)
                max_pp = max(max_pp, pp)

                print("MAX PROFIT = %f" % max_profit)
                print("MAX PROFIT, %% = %f %%" % max_pp)

            # trade
            if True:
                amount_to_buy1 = convert(amount_to_spend0, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], fee=0)
                amount_recieved1, sink = try_buy(amount_to_buy1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
                if (amount_recieved1 - config.eps) > 0:
                    amount_to_buy2 = convert(amount_recieved1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], fee=0)
                    amount_recieved2, usd_amount = try_buy(amount_to_buy2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                    if (amount_recieved2 - config.eps) > 0:
                        #final_amount = market_sell(amount_recieved2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

                        amount_to_buy0 = convert(amount_recieved2, from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0], fee=0)
                        final_amount, sink = try_buy(amount_to_buy0, from_coin=arbitrage_coins[2],  to_coin=arbitrage_coins[0])

                        profit = final_amount + usd_amount - amount_to_spend0 * (1 + config.tx)
                        sum_profit += profit

                        if profit > 0:
                            print("PROFIT = %f" % (profit))
                            ok_arb_count += 1
                        else:
                            print("LOSS = %f" % (profit))
                            failed_arb_count += 1


                    else:
                        #LOSS
                        loss = usd_amount - amount_to_spend0 * (1 + config.tx)
                        sum_profit += loss
                        print("LOSS = %f" % (loss))
                        failed_arb_count += 1

                    print("SUM PROFIT/LOSS = %f" % (sum_profit))
                    print("P:%f L:%f" % (ok_arb_count, failed_arb_count))

                    if sum_profit < config.max_loss:
                        break


'''
1. Aggregation should help against TOO SMALL
    NO EFFECT on thousands of arbitrages

!2. FAILED ARB could be fixed by simultaneous orders with some position in arb_coins

+- 3. 2FIX - false fee assumption during USDT-BTC trade
+- 3a. 2FIX - INSUFFICIENT FUNDS - convert(convert(convert)

!4. 2DO: command line iface for research, i.e.: start.py EXCHANGE COIN1 COIN2 COIN3

5. 2DO: .csv or other output fmt for further analysis - freq of arb, size of arb(avg, max), freq of trades

6. reduce verbosity of logs - too_smalls, order dumps - could be hidden

7. 2DO: fix crash on 'no response' from exchange

'''