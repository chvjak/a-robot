from bittrex import bittrex
from hitbtc import hitbtc

exchange = hitbtc("", "")
ob = exchange.order_book_aggregated_top1(from_coin='USD', to_coin='BTC', min_trade=10, cached = False)


exchange = bittrex("", "")

ob = exchange.order_book_aggregated_top1("USDT", "BTC", 1000000, cached = False)
print(ob)

ob = exchange.order_book_aggregated_top1("BTC", "USDT", 100, cached = False)
print(ob)

exit()
# get 0.1 btc for X usd priced as 10 usd per btc
order = exchange.create_order("USDT", "BTC", 0.1, 10)
if not order:
    print("could not create an order")
    exit()

print("order uuid = %s" % order)

is_open = exchange.is_order_open(order)
remaining_amount = exchange.order_remaining_amount(order)
print("is_open %s" % is_open )
print("remaining_amount  = %f" % remaining_amount)

print("closing order...")
exchange.cancel_order(order)
is_open = exchange.is_order_open(order)
print("is_open %s" % is_open)


# get 1 dollar for X btc priced as 10000 usd per btc
order = exchange.create_order("BTC", "USDT", 1, 1/10000)

if not order:
    print("could not create an order")
    exit()

print("order uuid = %s" % order)
is_open = exchange.is_order_open(order)
remaining_amount = exchange.order_remaining_amount(order)
print("is_open %s" % is_open )
print("remaining_amount  = %f" % remaining_amount)

print("closing order...")
exchange.cancel_order(order)
is_open = exchange.is_order_open(order)
print("is_open %s" % is_open)

