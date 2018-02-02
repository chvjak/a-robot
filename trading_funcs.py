from config import config

exchange = None
def get_min_trade(trade_coin):
    if trade_coin == config.BTC:
        return config.min_trade_btc
    else:
        return convert(config.min_trade_btc, from_coin=config.BTC, to_coin=trade_coin, fee=0, aggregation_volume=0)


def get_price(from_coin, to_coin, cached = True, aggregation_volume=None):

    if aggregation_volume is None:
        aggregation_volume = get_min_trade(from_coin)

    ob = exchange.order_book_aggregated_top1(from_coin, to_coin,  aggregation_volume, cached)
    return float(ob['price'])


def convert(amount_from, from_coin, to_coin, fee = config.tx, cached=True, aggregation_volume=None):
    if aggregation_volume is None:
        aggregation_volume = amount_from

    price = get_price(from_coin, to_coin, cached=cached, aggregation_volume=aggregation_volume)
    amount_to = amount_from / price * (1 - fee)

    return amount_to