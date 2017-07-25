from time import time

from gdax import gdax
from bitfinex import bitfinex
from poloniex import poloniex
from btce import btce
from gemini import gemini
from bittrex import bittrex
from kraken import kraken

class config:
        timeout   = 5
        trade_vol = 1
        test_vol  = 1
        tx        = 0.0025
        eps = 0.000001

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


    ARBITRAGE_PRICE = get_price(from_coin, to_coin)                       # 2FIX: this is excessive call, could be passed from outside or cached

    print("Trying to buy %f of %s for %s ." % (amount_to, to_coin, from_coin))
    order = exchange.create_order(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)

    time2 = time1 = time()
    while time2 - time1 < config.timeout and exchange.is_order_open(order):
        time2 = time()

    if exchange.is_order_open(order):
        print("Order for %f %s was not executed during timeout." % (amount_to, to_coin))
        remaining_amount_to = exchange.order_remaining_amount(order)
        print("Remaining amount is %f" % remaining_amount_to)
        exchange.cancel_order(order)                                      # remaining amount could change between this 2 calls! => market_order will fail

        actual_amount_to = amount_to - remaining_amount_to
        actual_amount_to *= (1 - config.tx)

        if from_coin != "USDT" and actual_amount_to > 0:
            order = exchange.market_order(from_coin, "USDT", remaining_amount_to)    # 2DO: calculate loss

    else:
        print("Order for %f %s was executed " % (amount_to, to_coin))
        actual_amount_to = amount_to
        actual_amount_to *= (1 - config.tx)

    print("Actual bought amount = %f %s" % (actual_amount_to, to_coin))

    return actual_amount_to

def get_price(from_coin, to_coin):
    '''
    :param from_coin:
    :param to_coin:
    :return: volume of order in the order book for sale of 'from_coin' currency to_coin 'to_coin' currency

    possibly agregate several orders if arbitrage still exists
    '''

    # ob[i] = {volume: 100; price: 55.56}
    # ob is sorted by price, ascending

    ob = exchange.order_book_top1(from_coin, to_coin)
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

def convert(amount_from, from_coin, to_coin):
    '''
    :param amount_from:
    :param to_coin:
    :return: amount of 'to_coin' currency if traded 'amount_from' amount of 'from_coin' currency considering current prices and tx fees
    '''
    price = get_price(from_coin, to_coin)

    fee = 0
    #fee = config.tx

    amount_to = amount_from / price * (1 - fee)

    print("%f %s in %s is %f" % (amount_from, from_coin, to_coin, amount_to))

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


    #kraken
    #arbitrage_coins = ['USD', 'ETH', 'XBT']

    #btce, #bitfinex
    #arbitrage_coins = ['usd', 'eth', 'btc']

    #bittrex, poloniex
    arbitrage_coins = ['USDT', 'ETH', 'BTC']
    #arbitrage_coins = ['BTC', 'LTC', 'ETH']
    #arbitrage_coins = ['USDT', 'LTC', 'ETH']
    #arbitrage_coins = ['USDT', 'ZEC', 'ETH']
    #arbitrage_coins = ['USDT', 'ZEC', 'BTC']
    #arbitrage_coins = ['USDT', 'ETH', 'DASH']
    #arbitrage_coins = ['USDT', 'BTC', 'DASH']
    #arbitrage_coins = ['USDT', 'BTC', 'XRP']
    #arbitrage_coins = ['USDT', 'ETH', 'XRP']






    max_profit = 0
    max_pp = 0
    sum_profit = 0
    while 1:
        pairs = get_relevant_pairs(exchange, arbitrage_coins)
        exchange.quotes = dict(zip(pairs, pool.map(exchange.returnOrderBook, pairs)))

        print()


        arb1 = convert(convert(convert(config.test_vol, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0]) - config.test_vol
        arb2 = convert(convert(convert(config.test_vol, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0]) - config.test_vol


        if arb1 > 0 or arb2 > 0:
            if arb2 > arb1:
                arbitrage_coins[1], arbitrage_coins[2] = arbitrage_coins[2], arbitrage_coins[1]

            # ARBITRAGE DETECTED
            print("ARBITRAGE DETECTED")

            # get available volume V from_coin order book
            V_UE1 = get_vol(from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])

            V2 = get_vol(from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
            V_UE2 = convert(V2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0])

            V3 = get_vol(from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
            V_UE3 = convert(V3, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

            V1 = min(V_UE1, V_UE2, V_UE3, config.trade_vol)         # ARBITRAGE AMOUNT

            # probing code
            if True:
                print("ARBITRAGE AMOUNT: %f" % V1)

                V3 = convert(convert(convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
                p = (V3 - V1)
                pp = (100 * (V3 / V1 - 1))

                print("ARBITRAGE PROFIT: %f" % p)
                print("ARBITRAGE PROFIT,%%: %f %%" % pp)

                max_profit = max(max_profit, p)
                max_pp = max(max_pp, pp)

                sum_profit += p
                print("SUM PROFIT = %f" % sum_profit )
                print("MAX PROFIT = %f" % max_profit)
                print("MAX PROFIT, %% = %f %%" % max_pp)

            # trade
            if False:
                V1_to = convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
                V2 = try_buy(V1_to, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
                if (V2 - config.eps) > 0:
                    V2_to = convert(V2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                    V3 = try_buy(V2_to, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                    if (V3 - config.eps) > 0:
                        V3_to = convert(V3, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
                        V1_final = try_buy(V3, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
                        if (V1_final - config.eps) > 0:
                            print("PROFIT = %f" % (V1_final - V1))
                            break

                    else:
                        #LOSS
                        print("LOSS")       # how much?
                        break


