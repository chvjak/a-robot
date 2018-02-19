class config:
        timeout                 = 100             # sec
        max_exposure            = 50            # USD
        test_vol                = 600           # USD, not used?
        trade_vol               = 10             # USD, EXCHANGE?
        tx                      = 0.002        # %,    EXCHANGE
        min_trade_btc           = 0.0005        # BTC, EXCHANGE
        eps                     = 0.00000001
        max_loss                = -1            # USD
        cooldown_time           = 5             # sec
        trade_vol_percent_min   = 5             # %
        ob_max_age_delta        = 3             # sec
        always_close_pos        = False
        trade                   = False
        init_dust_from_balance  = False

        USD                     = 'USDT'        # 'USDT' is 'USD' on hitbtc, EXCHANGE
        BTC                     = 'BTC'         # could be XBT, EXCHANGE

