from time import time, sleep, strftime, localtime
import math
import signal
from multiprocessing import Pool

from bittrex import bittrex
from config import config
from log import Log, DB

try:
    from keys import bittrex_keys
except ImportError:
    class bittrex_keys:
        api_key = ""
        api_secret = ""

AC2 = "BCC"
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


def insert_data():
    version = 1
    data = [dt(),
            arb_execution_time,
            profit,
            expected_profit,
            amount_to_spend_ul0,
            vols[pairs[0]][0],
            vols[pairs[0]][1],
            vols[pairs[0]][2],
            vols[pairs[1]][0],
            vols[pairs[1]][1],
            vols[pairs[1]][2],
            vols[pairs[2]][0],
            vols[pairs[2]][1],
            vols[pairs[2]][2],
            arb_stage_pass,

            arbitrage_coins[1],
            arbitrage_coins[2],

            get_price(arbitrage_coins[0], arbitrage_coins[1]),
            get_price(arbitrage_coins[1], arbitrage_coins[2]),
            get_price(arbitrage_coins[2], arbitrage_coins[0]),

            get_price(arbitrage_coins[0], arbitrage_coins[1], aggregation_volume=config.test_vol),
            get_price(arbitrage_coins[1], arbitrage_coins[2], aggregation_volume=config.test_vol),
            get_price(arbitrage_coins[2], arbitrage_coins[0], aggregation_volume=config.test_vol),
            version
            ]

    db.insert(data)


def signal_handler(signal, frame):
    log("Keyboard interrup")
    Log.f.flush()
    db.f.flush()
    exit(0)


def check_pl(sum_profit, sum_loss, dust):
    sum_dust = dust2coin0(dust)
    sum_pl = sum_profit + sum_loss + sum_dust
    log("***SUM PROFIT/LOSS = %f" % sum_pl)
    log("***EXPOSURE = %f" % sum_dust)
    log("***DUST = %s" % dust.__str__())

    # TODO: add max exposure check. E.i close exposre, check P/L and continue
    #if sum_dust > config.max_exposure: s, us = sell_dust(dust); profit += s

    if sum_pl < config.max_loss or sum_dust > config.max_exposure:
        log("===FIXING THE LOSS")
        sold, unsold = sell_dust(dust)
        log("final P/L = %f" % (sum_profit + sum_loss + sold))
        if sum(unsold.values()) > config.eps:
            log("...and some dust %f" % (unsold))
        exit()


def sell_dust(dust):
    res = 0
    small_dust = {}
    for (coin, amount) in dust.items():
        sold, unsold = market_sell(amount, from_coin=coin, to_coin=arbitrage_coins[0])
        res += sold
        small_dust[coin] = unsold

    return res, small_dust


def dust2coin0(dust):
    res = sum(convert(amount, from_coin=coin, to_coin=arbitrage_coins[0], fee=0, aggregation_volume=0) for (coin, amount) in dust.items())
    return res


def dt():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())


def t():
    return strftime("%H:%M:%S", localtime())


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


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
    #return None       # temporary disable aggregation in some contexts

    if trade_coin == arbitrage_coins[0]:
        return config.test_vol
    else:
        return convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=trade_coin, fee=0, aggregation_volume=0)


def get_min_trade(trade_coin):
    if trade_coin == "BTC":
        return config.min_trade_btc
    else:
        return convert(config.min_trade_btc, from_coin="BTC", to_coin=trade_coin, fee=0, aggregation_volume=0)


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

    price = get_price(from_coin, to_coin, cached=cached, aggregation_volume=aggregation_volume)
    amount_to = amount_from / price * (1 - fee)

    return amount_to


def create_order_timeout(from_coin, to_coin, amount_to, price):
    log("Trying to buy %10.10f of %s for %10.10f %s (price = %f %s)." %
          (amount_to, to_coin, amount_to * price, from_coin, price, from_coin))

    order = exchange.create_order(from_coin, to_coin, amount_to, price)
    if order != -1:
        time2 = time1 = time()
        while time2 - time1 < config.timeout and exchange.is_order_open(order):
            print('.',end='')
            time2 = time()
    else:
        log("Could not create order.")

    if order == -1 or (exchange.is_order_open(order) and exchange.cancel_order(order)):
        if order == -1:
            remaining_amount_to = amount_to
        else:
            log("- Order for %10.10f %s WAS NOT executed during timeout." % (amount_to, to_coin))
            remaining_amount_to = exchange.order_remaining_amount(order)

        log("Remaining amount is %10.10f" % remaining_amount_to)
    else:
        log("+ Order for %10.10f %s WAS EXECUTED " % (amount_to, to_coin))
        remaining_amount_to = 0

    return remaining_amount_to


def try_buy(amount_to, from_coin, to_coin):
    ARBITRAGE_PRICE = get_price(from_coin, to_coin, aggregation_volume=get_agam(from_coin))
    remaining_amount_to = create_order_timeout(from_coin, to_coin, amount_to, ARBITRAGE_PRICE)
    actual_amount_to = amount_to - remaining_amount_to

    if remaining_amount_to < config.eps:
        actual_amount_to = amount_to
        usd_amount = 0
        unsold_amount_from = 0

        if to_coin != AC2:
            actual_amount_to *= (1 - config.tx)
    else:
        if config.always_close_pos and from_coin != arbitrage_coins[0] and remaining_amount_to > get_min_trade(to_coin):
            if from_coin == "BTC" and to_coin == AC2:
                remaining_amount_to *= (1 + config.tx)

            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE                        # use 'sell price' to recover remaining unsold amount, actually it is availble as order property
            log("remaining_amount_from = %f, PRICE = %f" % (remaining_amount_from, ARBITRAGE_PRICE))
            usd_amount, unsold_amount_from = market_sell(remaining_amount_from, from_coin, to_coin = arbitrage_coins[0])

            if to_coin == arbitrage_coins[0]:
                actual_amount_to += usd_amount
                usd_amount = 0
        else:
            remaining_amount_from = remaining_amount_to * ARBITRAGE_PRICE

            if from_coin == arbitrage_coins[0]:
                usd_amount = remaining_amount_from
                unsold_amount_from = 0
            else:
                usd_amount = 0
                unsold_amount_from = remaining_amount_from


    log("Actual bought amount = %10.10f %s" % (actual_amount_to, to_coin))
    return truncate(actual_amount_to, 8), truncate(usd_amount, 8), truncate(unsold_amount_from, 8)


def market_sell(amount_from, from_coin, to_coin):
    amount_to = convert(amount_from, from_coin, to_coin, fee=0)
    remaining_amount_from = amount_from
    res = 0
    loop_guard = 0
    while amount_to > get_min_trade(to_coin):
        if loop_guard == 10:
            exit()
        else:
            loop_guard += 1

        PRICE = get_price(from_coin, to_coin, cached=False, aggregation_volume=remaining_amount_from)
        amount_to = remaining_amount_from / PRICE
        log("remaining_amount_from = %f, PRICE = %f" % (remaining_amount_from, PRICE))
        log("UPDATED amount_to = %10.10f" % (amount_to))

        remaining_amount_to = create_order_timeout(from_coin, to_coin, amount_to, PRICE)
        actual_amount_to = amount_to - remaining_amount_to

        if remaining_amount_to < config.eps:
            res += amount_to
            amount_to = 0
            remaining_amount_from = 0
        else:
            log("The order was partially executed. Actual result amount is %10.10f %s " % (actual_amount_to, to_coin))
            res += actual_amount_to
            amount_to = remaining_amount_to

            remaining_amount_from = remaining_amount_to * PRICE

    res *= (1 - config.tx)

    log("Actual bought amount = %10.10f %s" % (res, to_coin))
    return res, remaining_amount_from

if __name__ == '__main__':

    signal.signal(signal.SIGINT, signal_handler)

    pool = Pool(3)

    exchange = bittrex(bittrex_keys.api_key, bittrex_keys.api_secret)
    #exchange = ExchangeMock()

    #kraken
    #arbitrage_coins = ['USD', 'ETH', 'XBT']

    #btce, #bitfinex
    #arbitrage_coins = ['usd', 'eth', 'btc']

    #bittrex, poloniex
    arbitrage_coins = ['USDT', AC2, 'BTC']


    too_small_count = 0
    arb_count = 0
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

    dust = {arbitrage_coins[1]:0, arbitrage_coins[2]:0}

    arb_stage_pass = 0
    profit = 0
    amount_to_spend_ul0 = 0
    arb_execution_time = 0
    expected_profit = 0


    pairs = get_relevant_pairs(exchange, arbitrage_coins)
    balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))
    with Log() as log, DB() as db:
        log(balances)
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

                if ob_dl_count % 50 == 0:
                    print(':%f sec' % (sum_ob_dl_time / ob_dl_count))
                    sum_ob_dl_time = 0

                if ob_dl_count % 500 == 0:
                    check_pl(sum_profit, sum_loss, dust)

            arb1 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0]) - config.test_vol
            arb2 = convert(convert(convert(config.test_vol, from_coin=arbitrage_coins[0], to_coin=arbitrage_coins[2]), from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[1]), from_coin=arbitrage_coins[1], to_coin=arbitrage_coins[0]) - config.test_vol

            if arb1 > 0 or arb2 > 0:
                time_prev_arb = time()

                arb_count += 1
                log("\n\n====================")
                log("ARBITRAGE DETECTED %d" % arb_count)

                if arb2 > arb1:
                    arbitrage_coins[1], arbitrage_coins[2] = arbitrage_coins[2], arbitrage_coins[1]

                # get available volume V from_coin order book
                # SEEMS this code is obsolette with aggregation
                # USEFUL to know amount_to_spend_ul0 for stats, and expected amount and best prices
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
                # WARNING: best (non-agregated) price is chosen
                V3 = convert(convert(convert(V1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1]), from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2]), from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])
                expected_profit = (V3 - V1)
                expected_profit_percent = (100 * (V3 / V1 - 1))

                log("ARBITRAGE AMOUNT: %f" % V1)
                log("ARBITRAGE UL AMOUNT: %f" % amount_to_spend_ul0)

                log("EXPECTED ARBITRAGE PROFIT: %f" % expected_profit)
                log("EXPECTED ARBITRAGE PROFIT,%%: %f %%" % expected_profit_percent)

                # trade
                if True:
                    arb_stage_pass = 0
                    # BUY
                    amount_to_buy1 = convert(amount_to_spend0, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1], fee=0, aggregation_volume=get_agam(arbitrage_coins[0]))
                    amount_recieved1, usd_amount1, dust0 = try_buy(amount_to_buy1, from_coin = arbitrage_coins[0], to_coin = arbitrage_coins[1])

                    if dust[arbitrage_coins[1]] > 0:
                        log("Adding %10.10f %s of dust" % (dust[arbitrage_coins[1]], arbitrage_coins[1]))
                        amount_recieved1 += dust[arbitrage_coins[1]]
                        dust[arbitrage_coins[1]] = 0


                    if (amount_recieved1 - get_min_trade(arbitrage_coins[1])) > 0:
                        arb_stage_pass = 1
                        # SELL/BUY
                        amount_to_buy2 = convert(amount_recieved1, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2], fee=0, aggregation_volume=get_agam(arbitrage_coins[1]))
                        amount_recieved2, usd_amount2, dust1 = try_buy(amount_to_buy2, from_coin = arbitrage_coins[1], to_coin = arbitrage_coins[2])
                        dust[arbitrage_coins[1]] += dust1

                        if dust[arbitrage_coins[2]] > 0:
                            log("Adding %10.10f %s of dust" % (dust[arbitrage_coins[2]], arbitrage_coins[2]))
                            amount_recieved2 += dust[arbitrage_coins[2]]
                            dust[arbitrage_coins[2]] = 0

                        if (amount_recieved2 - get_min_trade(arbitrage_coins[2])) > 0:
                            arb_stage_pass = 2
                            #final_amount, dust2 = market_sell(amount_recieved2, from_coin = arbitrage_coins[2], to_coin = arbitrage_coins[0])

                            # SELL
                            amount_to_buy0 = convert(amount_recieved2, from_coin=arbitrage_coins[2], to_coin=arbitrage_coins[0], fee=0, aggregation_volume=get_agam(arbitrage_coins[2]))
                            final_amount, sink, dust2 = try_buy(amount_to_buy0, from_coin=arbitrage_coins[2],  to_coin=arbitrage_coins[0])

                            dust[arbitrage_coins[2]] += dust2

                            profit = final_amount + usd_amount1 + usd_amount2 - amount_to_spend0 * (1 + config.tx)

                            arb_stage_pass = 3
                            if profit > 0:
                                log("+++PROFIT = %f" % (profit))
                                profit_count += 1
                                sum_profit += profit

                            else:
                                log("---LOSS = %f" % (profit))
                                loss_count += 1
                                sum_loss += profit

                        else:
                            dust2 = amount_recieved2
                            dust[arbitrage_coins[2]] += dust2

                            profit =  usd_amount1 + usd_amount2 - amount_to_spend0 * (1 + config.tx)
                            log("---LOSS = %f" % profit)
                            sum_loss += profit
                            loss_count += 1

                        arb_execution_time = time() - time_prev_arb

                        sum_arb_execution_time += arb_execution_time

                        min_arb_execution_time = min(min_arb_execution_time, arb_execution_time)
                        max_arb_execution_time = max(max_arb_execution_time, arb_execution_time)

                        vols = dict(zip(pairs, pool.map(exchange.get_market_volatility, pairs)))
                        balances = dict(zip(arbitrage_coins, pool.map(exchange.get_balance, arbitrage_coins)))

                        log("***AVG P:%f, L:%f" % (sum_profit / profit_count, sum_loss / loss_count))
                        log("P:%d L:%d" % (profit_count, loss_count))
                        log("ARBITRAGE TOOK %f sec" % (arb_execution_time))
                        log("EXECUTION TIME: AVG %f sec, MIN %f sec, MAX %f sec" % (sum_arb_execution_time/(profit_count + loss_count), min_arb_execution_time, max_arb_execution_time))
                        log(vols)
                        log(balances)

                        log("")

                        check_pl(sum_profit, sum_loss, dust)

                    else:
                        dust1 = amount_recieved1
                        dust[arbitrage_coins[1]] += dust1

                        log(">>>")

                    insert_data()


'''
0. Fix convert(convert()) => Use actual position instead of desired position  

2. FAILED ARB could be fixed by simultaneous orders with some position in arb_coins
    Seems doesn't make much sense since it increases exposure to market <= requires open positions for indefinite time

!4. 2DO: command line iface for research, i.e.: start.py EXCHANGE COIN1 COIN2 COIN3
!5. 2DO: .csv or other output fmt for further analysis - freq of arb, size of arb(avg, max), freq of trades
    - may be db is better due to possible simultaneous run of scripts. this might imply use of MPQUEUE for logging, + logging thread which outs data into db

8. SPEEDUP: avoid exchange roundtrip for remaining amount of order

    
+10. STATS: 
    +- check balances on start and on each a-ge, show stats
    - time from last arbitrage
    - avg p/l, avg a-ge for last several cases to track dynamics and use it for stop

ec2 deployment

[ec2-user@ip-172-31-22-16 ~]$ sudo yum list |grep python3
[ec2-user@ip-172-31-22-16 ~]$ sudo yum install python35
[ec2-user@ip-172-31-22-16 ~]$ curl -O https://bootstrap.pypa.io/get-pip.py
[ec2-user@ip-172-31-22-16 ~]$ python3 get-pip.py --user
[ec2-user@ip-172-31-22-16 ~]$ vi .bash_profile
                            add pip-path to $path
[ec2-user@ip-172-31-22-16 ~]$ source ./.bash_profile
[ec2-user@ip-172-31-22-16 ~]$ pip install requests --user

check pypy3 deployment:
    get pypy3.tar.gz
    download get-pip.py and continue as above
    

'''