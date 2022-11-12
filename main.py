from loan import Loan, get_my_coins_list

delete_orders_older_than_hours = 12

my_coin_list = get_my_coins_list()

for i in my_coin_list:
    lending_coin = Loan(i, delete_orders_older_than_hours)
    lending_coin.process_open_orders()
    lending_coin.lend_coin()
    del lending_coin

##TODO *args call to kucoin
##TODO only lend when process_open_orders returns an amount?
