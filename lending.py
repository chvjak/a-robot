from bitfinex import bitfinex
try:
    from keys import bitfinex_lender_keys
except ImportError:
    class bittrex_keys:
        api_key = ""
        api_secret = ""

exchange = bitfinex(bitfinex_lender_keys.api_key, bitfinex_lender_keys.api_secret)

# check for existing offers - cancel them
offers = exchange.get_offers()
for o in offers:
    exchange.cancel_offer(o['id'])

# get available lending balance for given coin
balances = exchange.get_balances()
#balances = [{'type': 'deposit', 'currency': 'usd', 'amount': '2.00003762', 'available': '200'}]

# offer funding at the price of 0.005 of all funds
small_fraction = 0.005

for b in balances:
    if b['type'] == 'deposit':
        if float(b['available']) > 0.001:
            print(b)
            # get lending book
            # consider limit_bids & limit_asks
            # rate is per annum

            book = exchange.get_lending_book(b['currency'])

            if len(book['asks']):
                total_offers = 0
                for a in book['asks']:
                    total_offers += float(a['amount'])

                small_fraction_sum = 0
                for a in book['asks']:
                    small_fraction_sum += float(a['amount'])
                    if small_fraction_sum  > total_offers * small_fraction:
                        break

                print('total offered ', total_offers )
                print('1% sum is ', small_fraction_sum )
                print('1% rate is ', float(a['rate']), float(a['rate']) / 365.0)

                rate = a['rate']


            # offer all balances at the 'top' rate
            exchange.create_offer(b['currency'], b['available'], str(rate), 2)



