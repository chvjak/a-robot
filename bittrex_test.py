from bittrex import bittrex
exchange = bittrex("286302f8d49f48b5b147418f193765c8", "328bb9193d324e918aec08dc0c814728")

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


# get 1 dollar for X btc priced as 3000 usd per btc
order = exchange.create_order("BTC", "USDT", 1, 1/3000)

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

