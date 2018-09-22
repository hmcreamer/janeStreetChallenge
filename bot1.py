#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
import time

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="TEAMBIGDATA"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    return json.loads(exchange.readline())

# sub functions and global vars

attempted_buy_positions = {}

attempted_sell_positions = {}

our_current_positions = {"BOND":0, "AAPL": 0, "MSFT": 0, "GOOG": 0, "XLK": 0, "BABA": 0, "BABZ": 0}

book = {"BOND": {}, "AAPL": {}, "MSFT": {}, "GOOG": {}, "XLK": {}, "BABA": {}, "BABZ": {}}

trades = {"BOND": [], "AAPL": [], "MSFT": [], "GOOG": [], "XLK": [], "BABA": [], "BABZ": []}

market_price = {"BOND": 1000, "AAPL": float('inf'), "MSFT": float('inf'), "GOOG": float('inf'), "XLK": float('inf'), "BABA": float('inf'), "BABZ": float('inf'), "EXXLK": float("inf")}

def read_message(message):
    if (message["type"] == str(book)):
        book[message["symbol"]] = {"sell": message["sell"], "buy": message["buy"]}

    elif (message["type"] == "reject"):
        if (message["order_id"] % 2 == 0):
            if (attempted_buy_positions.has_key(message["order_id"])):
                attempted_buy_positions.pop(message["order_id"])
        else:
            if (attempted_sell_positions.has_key(message["order_id"])):
                attempted_sell_positions.pop(message["order_id"])

    elif message["type"] == "trade":
        if len(trades[message["symbol"]]) < 5:
            trades[message["symbol"]].append(message["price"])
        else:
            trades[message["symbol"]].pop(0)
            trades[message["symbol"]].append(message["price"])

    elif (message["type"] == "fill"):
        if message["dir"] == "BUY":
            our_current_positions[message["symbol"]] += message["size"]
            attempted_sell_positions[message["order_id"]][2] -= message["size"]
            if attempted_sell_positions[message["order_id"]][2] <= 0:
                attempted_sell_positions.pop(message["order_id"])
        else:
            our_current_positions[message["symbol"]] -= message["size"]
            attempted_sell_positions[message["order_id"]][2] -= message["size"]
            if attempted_sell_positions[message["order_id"]][2] <= 0:
                attempted_sell_positions.pop(message["order_id"])

def buy_position(exchange, orderId, symbol, price, size):
    write_to_exchange(exchange, {"type": "add", "order_id": orderId, "symbol": symbol, "dir": "BUY", "price": price, "size": size})
    replyMessage = read_from_exchange(exchange)

def sell_position(exchange, orderId, symbol, price, size):
    write_to_exchange(exchange, {"type": "add", "order_id": orderId, "symbol": symbol, "dir": "SELL", "price": price, "size": size})
    replyMessage = read_from_exchange(exchange)

def convert_position(exchange, orderId, symbol, size, direction):
    write_to_exchange(exchange, {"type": "convert", "order_id": orderId, "symbol": symbol, direction: "BUY", "size": size})




def update_market_price():
    for symbol in trades.keys():
        market_price[symbol] = sum.trades[symbol]/5.0
    market_price["BOND"] = 1000
    market_price["EXBABA"] = market_price["BABZ"]
    market_price["EXXLK"] = ((3 * market_price["BOND"]) + (2 * market_price["APPL"]) + (3 * market_price["MSFT"]) + (2 * market_price["GOOG"]))/10.0


def buysell(exchange, symbol):
    for sell in book[symbol]["sell"]:
        if (sell < market_price[symbol]):
            amount_wanted = sell[1]
            amount_possible = our_current_positions[symbol]
            if (amount_wanted <= amount_possible):
                to_sell = amount_wanted
            else:
                to_sell = amount_possible
            sell_position(exchange, 0, symbol, sell[0], to_sell)
            our_current_positions[symbol] -= to_sell

    for buy in book[symbol]["buy"]:
        if (buy > market_price[symbol]):
            amount_offered = buy[1]
            amount_possible = 100 - our_current_positions[symbol]
            if (amount_offered <= amount_possible):
                to_buy = amount_offered
            else:
                to_buy = amount_possible

            buy_position(exchange, 0, symbol, buy[0], to_buy)
            our_current_positions[symbol] += to_buy

def exchange(exchange):
    if ((market_price["BABA"] * our_current_positions["BABA"]) + 10 < (market_price["BABZ"] * our_current_positions["BABA"])):
        convert_position(exchange, 0, "BABA", our_current_positions["BABA"], "SELL")

    if (market_price["XLK"] * our_current_positions["XLK"] + 100 < market_price["EXXLK"] * our_current_positions["LKX"]):
        convert_position(exchange, 0, "XLK", our_current_positions["XLK"], "SELL")

# ~~~~~============== MAIN LOOP ==============~~~~~


def main(wait_time, exchange):
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!


    # We need to read the messages and do stuff accordingly

    messages = read_from_exchange(exchange)
    #print("string messages: ")
    #print(messages)
    read_message(messages)
    update_market_price()
    for symbol in market_price.keys():
        buysell(exchange, symbol)
    exchange(exchange)

    # At end of loop, we want to:
    # 1. clear all of our dictionaries
    # 2. reset order id numbers
    # 3. reconnect to server using linux command

def run_bot():
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)
    start_time = time.time()
    wait_time = 0
    while wait_time <=300:
        wait_time = start_time - time.time()
        main(wait_time, exchange)
        # Add logger for parsing server messges for other people's trades





if __name__ == "__main__":
    run_bot()


"""    
{u'sell': [[4000, 2], [4001, 3], [4002, 11]], u'symbol': u'MSFT', u'buy': [[3996, 2], [3995, 4], [3994, 2]], u'type': u'book'}
The exchange replied: {u'symbols': [{u'position': 0, u'symbol': u'AAPL'}, {u'position': 0, u'symbol': u'BABA'}, 
{u'position': 0, u'symbol': u'BABZ'}, {u'position': 0, u'symbol': u'BOND'}, {u'position': 0, u'symbol': u'GOOG'}, 
{u'position': 0, u'symbol': u'MSFT'}, {u'position': 0, u'symbol': u'USD'}, 
{u'position': 0, u'symbol': u'XLK'}], u'type': u'hello'}
{u'symbols': [u'AAPL', u'BABA', u'BABZ', u'BOND', u'GOOG', u'MSFT', u'XLK'], u'type': u'open'}
"""
