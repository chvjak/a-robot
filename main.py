from time import time, sleep, strftime, localtime

from bittrex import bittrex
from config import config

try:
    from keys import bittrex_keys
except ImportError:
    class bittrex_keys:
        api_key = ""
        api_secret = ""

AC2 = "NEO"
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


def get_agam(trade_coin):
    '''
        Get AGregated AMount = test_vol cpnverted to trade_coin
    '''
    return None       # temporary disable aggregation in some contexts

    if trade_coin == "USDT":
        return config.test_vol
    else:
        return convert(config.test_vol, from_coin="USDT", to_coin=trade_coin, fee=0, aggregation_volume=0)


def get_min_trade(trade_coin):
    if trade_coin == "BTC":
        return config.min_trade_btc
    else:
        return convert(config.min_trade_btc, from_coin="BTC", to_coin=trade_coin, fee=0, aggregation_volume=0)


def try_buy(amount_to, from_coin, to_coin):
    print("Trying to buy %f of %s for %s." % (amount_to, to_coin, from_coin))
    ARBITRAGE_PRICE = get_price(from_coin, to_coin, aggregation_volume=get_agam(from_coin))

    print("ARBITRAGE_PRICE = %f %s." % (ARBITRAGE_PRICE, from_coin))
    order = exchange.create_order(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)

    if order != -1:

        time2 = time1 = time()
        while time2 - time1 < config.timeout and exchange.is_order_open(order):
            print('.',end='')
            time2 = time()
    else:
        print("Could not create order.")

    print()
    if order == -1 or (exchange.is_order_open(order) and exchange.cancel_order(order)):
        if order == -1:
            remaining_amount_to = amount_to
        else:
            print("Order for %10.10f %s was not executed during timeout." % (amount_to, to_coin))
            remaining_amount_to = exchange.order_remaining_amount(order)

        print("Remaining amount is %10.10f" % remaining_amount_to)
        actual_amount_to = amount_to - remaining_amount_to

        if from_coin != "USDT" and remaining_amount_to > get_min_trade(to_coin):
            # if BTC->BCC conversion fails, BTC->USDT conversion follows and reserved tx fee was not spent
            # BUT if it was BCC->BTC transaction the source of BTC then there is no unused fee
            # 2FIX: better fix needed. E.g get to ACTUAL from_amounts, OR use info from order, implies caching of order info
            if from_coin == "BTC" and to_coin == AC2:
                print("Increasing BTC amount to reflect unuset comission")
                print("before increse = %f" % remaining_amount_to)
                remaining_amount_to *= (1 + config.tx)
                print("after increse = %f" % remaining_amount_to)

            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE                        # use 'sell price' to recover remaining unsold amount, actually it is availble as order property
            print("remaining_amount_from = %f, PRICE = %f" % (remaining_amount_from, ARBITRAGE_PRICE))
            usd_amount = market_sell(remaining_amount_from, from_coin, to_coin = "USDT")

            if to_coin == "USDT":
                actual_amount_to += usd_amount
                usd_amount = 0
        else:
            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE
            usd_amount = remaining_amount_from
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

        if exchange.is_order_open(order) and exchange.cancel_order(order):
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

    res *= (1 - config.tx)

    # TODO: return amount_to for situations when it's 'dust'
    # SEEMS it would make more as amount_from (+ currency)
    # OR check the balance before the trade and use up all available coin - seems too bold

    print("Actual bought amount = %10.10f %s" % (res, to_coin))
    return res

def get_vol(from_coin, to_coin, aggregation_volume = None):
    if aggregation_volume is None:
        aggregation_volume = get_min_trade(from_coin)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin, aggregation_volume, cached = True)
    return ob['volume']

def get_price(from_coin, to_coin, cached = True, aggregation_volume = None):
    if aggregation_volume is None:
        aggregation_volume = get_min_trade(from_coin)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin,  aggregation_volume, cached)
    return float(ob['price'])

def convert(amount_from, from_coin, to_coin, fee = config.tx, cached = True, aggregation_volume=None):
    if aggregation_volume is None:
        aggregation_volume = amount_from

    price = get_price(from_coin, to_coin, cached=cached, aggregation_volume=amount_from)
    amount_to = amount_from / price * (1 - fee)

    return amount_to


if __name__ == '__main__':
    from multiprocessing import Pool
    pool = Pool(3)

    exchange = bittrex(bittrex_keys.api_key, bittrex_keys.api_secret)
    #exchange = ExchangeMock()

    #kraken
    #arbitrage_coins = ['USD', 'ETH', 'XBT']

    #btce, #bitfinex
    #arbitrage_coins = ['usd', 'eth', 'btc']

    #bittrex, poloniex
    arbitrage_coins = ['USDT', AC2, 'BTC']


    max_profit = 0
    max_pp = 0
    too_small_count = 0
    arb_count = 0
    max_aa = 0
    time_prev_arb = 0

    min_arb_execution_time = 100
    max_arb_execution_time = 0
    sum_arb_execution_time = 0

    sum_ob_dl_time = 0
    ob_dl_count = 0
    
    sum_profit = 0
    sum_loss = 0

    profit_count = 1
    loss_count = 1

    print(strftime("%H:%M:%S", localtime()))

    pairs = get_relevant_pairs(exchange, arbitrage_coins)
    balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))
    print(balances)
    while 1:

        dl_start_time = time()
        exchange.quotes = dict(zip(pairs, pool.map(exchange.returnOrderBook, pairs)))

        ob_dl_count += 1
        sum_ob_dl_time += (time() - dl_start_time)

        if any(x is None for x in exchange.quotes.values()):
            sum_ob_dl_time = 0
            ob_dl_count = 0

            sleep(config.cooldown_time)
            continue
        else:
            time1 = time()
            if any(abs(x['time'] - time1) > config.ob_max_age_delta for x in exchange.quotes.values()):
                print('|', end='', flush=True)
                continue
            else:
                print('.', end='', flush=True)

            if ob_dl_count == 50:
                print(':%f sec' % (sum_ob_dl_time / ob_dl_count))
                sum_ob_dl_time = 0
                ob_dl_count = 0
                vols = dict(zip(pairs, pool.map(exchange.get_market_vol, pairs)))
                print(vols)

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
            # SEEMS this code is obsolette with aggregation
            av0 = config.test_vol
            av1 = convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1], fee=0)
            av2 = convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2], fee=0)
            amount_onsale_from0_to1_as0 = get_vol(from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], aggregation_volume=av0)

            amount_onsale_from1_to2_as1 = get_vol(from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], aggregation_volume=av1)
            amount_onsale_from1_to2_as0 = convert(amount_onsale_from1_to2_as1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[0], fee = 0)

            amount_onsale_from2_to0_as2 = get_vol(from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0], aggregation_volume=av2)
            amount_onsale_from2_to0_as0 = convert(amount_onsale_from2_to0_as2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0], fee = 0)

            amount_to_spend0 = min(amount_onsale_from0_to1_as0, amount_onsale_from1_to2_as0, amount_onsale_from2_to0_as0, config.trade_vol)         # ARBITRAGE AMOUNT
            amount_to_spend_ul0 = min(amount_onsale_from0_to1_as0, amount_onsale_from1_to2_as0, amount_onsale_from2_to0_as0)

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
                amount_to_buy1 = convert(amount_to_spend0, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], fee=0, aggregation_volume=get_agam(arbitrage_coins[0]))
                amount_recieved1, usd_amount1 = try_buy(amount_to_buy1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])
                print(strftime("%H:%M:%S", localtime()))
                if (amount_recieved1 - get_min_trade(arbitrage_coins[1])) > 0:
                    amount_to_buy2 = convert(amount_recieved1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], fee=0, aggregation_volume=get_agam(arbitrage_coins[1]))
                    amount_recieved2, usd_amount = try_buy(amount_to_buy2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                    print(strftime("%H:%M:%S", localtime()))
                    if (amount_recieved2 - get_min_trade(arbitrage_coins[2])) > 0:
                        #final_amount = market_sell(amount_recieved2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

                        amount_to_buy0 = convert(amount_recieved2, from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0], fee=0, aggregation_volume=get_agam(arbitrage_coins[2]))
                        final_amount, sink = try_buy(amount_to_buy0, from_coin=arbitrage_coins[2],  to_coin=arbitrage_coins[0])

                        profit = final_amount + usd_amount1 + usd_amount - amount_to_spend0 * (1 + config.tx)

                        if profit > 0:
                            print("\n+++PROFIT = %f" % (profit))
                            profit_count += 1
                            sum_profit += profit

                        else:
                            print("\n---LOSS = %f" % (profit))
                            loss_count += 1
                            sum_loss += profit


                    else:
                        loss = usd_amount - amount_to_spend0 * (1 + config.tx)
                        print("\n---LOSS = %f" % (loss))
                        sum_loss += loss
                        loss_count += 1

                    arb_execution_time = time() - time_prev_arb

                    sum_arb_execution_time += arb_execution_time

                    min_arb_execution_time = min(min_arb_execution_time, arb_execution_time )
                    max_arb_execution_time = max(max_arb_execution_time, arb_execution_time)

                    print("***SUM PROFIT/LOSS = %f" % (sum_profit + sum_loss))
                    print("***AVG P:%f, L:%f" % (sum_profit / profit_count, sum_loss / loss_count))

                    print("P:%d L:%d" % (profit_count, loss_count))
                    print("ARBITRAGE TOOK %f sec" % (arb_execution_time))
                    print("EXECUTION TIME: AVG %f sec, MIN %f sec, MAX %f sec" % (sum_arb_execution_time/(profit_count + loss_count), min_arb_execution_time, max_arb_execution_time))
                    balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))
                    print(balances)
                    vols = dict(zip(pairs, pool.map(exchange.get_market_vol, pairs)))
                    print(vols)

                    print("")

                    if sum_profit + sum_loss < config.max_loss:
                        break
                else:
                    print(">>>")


'''
    0. Fix convert(convert()) => Use actual position instead of desired position => this would fix 1a 

+-! 1. Aggregation should help against TOO SMALL
    1a Problem with agam()      

2. FAILED ARB could be fixed by simultaneous orders with some position in arb_coins
    Seems doesn't make much sense since it increases exposure to market <= requires open positions for indefinite time

++- 3. 2FIX - false fee assumption during USDT-BTC trade
++- 3a. 2FIX - INSUFFICIENT FUNDS on market_sell

!4. 2DO: command line iface for research, i.e.: start.py EXCHANGE COIN1 COIN2 COIN3
!5. 2DO: .csv or other output fmt for further analysis - freq of arb, size of arb(avg, max), freq of trades
    - may be db is better due to possible simultaneous run of scripts. this might imply use of MPQUEUE for logging, + logging thread which outs data into db

8. SPEEDUP: avoid exchange roundtrip for remainig amount of order

-++9. 2FIX: 300 sec waits for order execution. This might be long r4esponse from exchange
    a. time_out on create_order
    - on order create/is open - most dangerous. If First order took too long => close position
    - if is_open timedout => stop(?)
    - probably cooldown in this cases 
    
    10. STATS: 
        +- check balances on start and on each a-ge, show stats
        - time from last arbitrage
        - avg p/l, avg a-ge for last several cases to track dynamics and use it for stop

ec2 deployment

[ec2-user@ip-172-31-22-16 ~]$ sudo yum list |grep python3
[ec2-user@ip-172-31-22-16 ~]$ sudo yum install python35
[ec2-user@ip-172-31-22-16 ~]$ curl -O https://bootstrap.pypa.io/get-pip.py
[ec2-user@ip-172-31-22-16 ~]$ python3 get-pip.py --user
[ec2-user@ip-172-31-22-16 ~]$ vi .bash_profile
[ec2-user@ip-172-31-22-16 ~]$ source ./.bash_profile
[ec2-user@ip-172-31-22-16 ~]$ pip install requests --user

'''