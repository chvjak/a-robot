from time import time
from poloniex import poloniex
from btce import btce
from bittrex import bittrex
from kraken import kraken

class config:
        timeout = 5
        trade_vol = 10
        test_vol = 10


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
    order = exchange.create_order(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)

    time2 = time1 = time()
    while time2 - time1 < config.timeout and exchange.is_order_open(order):
        time2 = time()

    if exchange.is_order_open(order):
        remaining_amount_to = exchange.order_remaining_amount(order)
        exchange.cancel_order(order)                                      # remaining amount could change between this 2 calls! => market_order will fail

        actual_amount_to = amount_to - remaining_amount_to
        exchange.market_order(from_coin, to_coin, remaining_amount_to)    # 2DO: calculate loss
    else:
        actual_amount_to = amount_to

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

    #amount_to = amount_from / price - exchange.tx_fee(from_coin, to_coin)
    amount_to = amount_from / price
    
    #print("%f %s in %s is %f" % (amount_from, from_coin, to_coin, amount_to))

    return amount_to



#exchange = poloniex("", "")
#exchange = btce("", "")
#exchange = kraken("", "")


exchange = bittrex("", "")
#exchange = bittrex("3d67ccf43be1415094a18f625a82ced1", "825725094abf448a96cf6864f4047dfc")


#arbitrage_coins = ['USD', 'ETH', 'XBT']
#arbitrage_coins = ['USD', 'ETH', 'BTC']

#bittrex
#arbitrage_coins = ['USDT', 'ETH', 'BTC']
#arbitrage_coins = ['USDT', 'ZEC', 'ETH']
#arbitrage_coins = ['USDT', 'ZEC', 'BTC']

arbitrage_coins = ['USDT', 'ETH', 'DASH']          #2.387044 %
#arbitrage_coins = ['USDT', 'BTC', 'DASH']          #1.406602 %
#arbitrage_coins = ['USDT', 'BTC', 'XRP']           #0.6%
#arbitrage_coins = ['USDT', 'ETH', 'XRP']           #1.13%



profit = 0
while 1:
    # get pair tickers BTC, ETH, USDT, get order books
    # exchange.update()

    # check if 10 USDT => X ETH => Y BTC => Z USDT > 10:
    # DOES I MATTER? check if 10 USDT => X BTC => Y ETH => Z USDT > 10:

    print()

    # NOTE that V1 is V1 * 0.9975
    # NOTE that V2 is V2 * 0.9950
    # NOTE that V3 is V3 * 0.9925
    if convert(convert(convert(config.test_vol, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0]) > config.test_vol:
        # ARBITRAGE DETECTED
        print("ARBITRAGE DETECTED")

        # get available volume V from_coin order book
        V_UE1 = get_vol(from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])

        V2 = get_vol(from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
        V_UE2 = convert(V2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0])

        V3 = get_vol(from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
        V_UE3 = convert(V3, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

        #V1 = min(V_UE1, V_UE2, V_UE3, config.trade_vol)         # ARBITRAGE AMOUNT

        V1 = min(V_UE1, V_UE2, V_UE3)  # ARBITRAGE AMOUNT

        print("ARBITRAGE AMOUNT: %f" % V1)

        V3 = convert(convert(convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

        print("ARBITRAGE PROFIT: %f" % (V3 - V1))
        print("ARBITRAGE PROFIT,%%: %f %%" % (100 * (V3 / V1 - 1)))


        if 100 * (V3 / V1 - 1) > 0.75:
            p = (V3 - V1)
            clean_p = p  #- V1 * 0.0025 - V2 * 0.0025 - V3 * 0.0025
            profit += clean_p
            print("HUGE PROFIT = %f" % profit)


'''
        # trade
        if try_buy(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]):
            V2 = convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
            if try_buy(V2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]):
                V3 = convert(V2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                if try_buy(V3, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]):
                    #PROFIT/#LOSS
            else:
                #LOSS
                ...
'''