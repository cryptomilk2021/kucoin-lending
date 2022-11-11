from loan import Loan, get_my_coins_list

delete_orders_older_than_hours = 12

my_coin_list = get_my_coins_list()

for i in my_coin_list:
    lending_coin = Loan(i, delete_orders_older_than_hours)
    lending_coin.process_open_orders()
    lending_coin.lend_coin()
    del lending_coin

##TODO no writing to .csv
##TODO *args call to kucoin
##TODO only lend when process_open_orders returns an amount?
#TODO convert precision file to dict as well as not lendable coins
#TODO find optimal amounts to lend ie. >USDT20, breaks into 0.00ETH, cannot lend ETH even though it's more than USDT10
#todo BAT has minimum of 10....