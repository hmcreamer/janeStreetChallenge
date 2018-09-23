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
from collections import defaultdict
import random

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="TEAMBIGDATA"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

order_idxxx = 1

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

book = {"BOND": {"sell": [], "buy": []},
        "AAPL": {"sell": [], "buy": []},
        "MSFT": {"sell": [], "buy": []},
        "GOOG": {"sell": [], "buy": []},
        "XLK": {"sell": [], "buy": []},
        "BABA": {"sell": [], "buy": []},
        "BABZ": {"sell": [], "buy": []},
        "EXXLK": {"sell": [], "buy": []},
        "EXBABA": {"sell": [], "buy": []},
        }

trades = {"BOND": [], "AAPL": [], "MSFT": [], "GOOG": [], "XLK": [], "BABA": [], "BABZ": []}

market_price = {"BOND": 1000, "AAPL": float('inf'), "MSFT": float('inf'), "GOOG": float('inf'), "XLK": float('inf'), "BABA": float('inf'), "BABZ": float('inf'), "EXXLK": float("inf")}

def read_message(message):
    if (message["type"] == "book"):
        #print("in book")
        #print(message["sell"])
        #print(message["buy"])
        book[message["symbol"]] = {"sell": message["sell"], "buy": message["buy"]}
        #print(book)


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
            #print("added")
        else:
            trades[message["symbol"]].pop(0)
            trades[message["symbol"]].append(message["price"])

    elif (message["type"] == "fill"):
        if message["dir"] == "BUY":
            our_current_positions[message["symbol"]] += message["size"]
            # attempted_sell_positions[message["order_id"]][2] -= message["size"]
            # if attempted_sell_positions[message["order_id"]][2] <= 0:
            #     attempted_sell_positions.pop(message["order_id"])
        else:
            our_current_positions[message["symbol"]] -= message["size"]
            attempted_sell_positions[message["order_id"]][2] -= message["size"]
            if attempted_sell_positions[message["order_id"]][2] <= 0:
                attempted_sell_positions.pop(message["order_id"])

def buy_position(exchange, orderId, symbol, price, size):
    write_to_exchange(exchange, {"type": "add", "order_id": orderId, "symbol": symbol, "dir": "BUY", "price": price, "size": size})
    attempted_buy_positions[orderId] = [symbol, price, size]


def sell_position(exchange, orderId, symbol, price, size):
    write_to_exchange(exchange, {"type": "add", "order_id": orderId, "symbol": symbol, "dir": "SELL", "price": price, "size": size})
    attempted_sell_positions[orderId] = [symbol, price, size]

def convert_position(exchange, orderId, symbol, size, direction):
    write_to_exchange(exchange, {"type": "convert", "order_id": orderId, "symbol": symbol, direction: "BUY", "size": size})



def update_market_price():
    for symbol in trades.keys():
        market_price[symbol] = sum(trades[symbol])/float(len(trades[symbol])+ .00000001)

    market_price["BOND"] = 1000
    market_price["EXBABA"] = market_price["BABZ"]
    market_price["EXXLK"] = ((3 * market_price["BOND"]) + (2 * market_price["AAPL"]) + (3 * market_price["MSFT"]) + (2 * market_price["GOOG"]))/10.0


def buysell(exchange, symbol, wait_time):
    for sell in book[symbol]["sell"]:
        if (sell > 1.5 + market_price[symbol]):
            print("sell")
            amount_wanted = sell[1]
            amount_possible = our_current_positions[symbol]
            if (amount_wanted <= amount_possible):
                to_sell = amount_wanted
            else:
                to_sell = amount_possible
            sell_position(exchange, wait_time, symbol, sell[0] - 1, to_sell)
            our_current_positions[symbol] -= to_sell

    for buy in book[symbol]["buy"]:
        if (buy > market_price[symbol]):
            print("buy")
            amount_offered = buy[1]
            amount_possible = 100 - our_current_positions[symbol]
            if (amount_offered <= amount_possible):
                to_buy = amount_offered
            else:
                to_buy = amount_possible

            buy_position(exchange, wait_time*2, symbol, buy[0], to_buy)
            our_current_positions[symbol] += to_buy



def converting(exchange, wait_time):
    if ((market_price["BABA"] * our_current_positions["BABA"]) + 8 < (market_price["BABZ"] * our_current_positions["BABA"])):

        if (10 - our_current_positions["BABZ"] >= our_current_positions["BABA"]):
            amount_converted = our_current_positions["BABA"]
            our_current_positions["BABA"] = our_current_positions["BABA"] - amount_converted
            our_current_positions["BABZ"] = amount_converted + our_current_positions["BABZ"]
        else:
            amount_converted = 10 - our_current_positions["BABZ"]
            our_current_positions["BABA"] = our_current_positions["BABA"] - amount_converted
            our_current_positions["BABZ"] = amount_converted + our_current_positions["BABZ"]

        convert_position(exchange, wait_time, "BABA", amount_converted, "SELL")


    if ((market_price["BABA"] * our_current_positions["BABA"]) > 8 + (market_price["BABZ"] * our_current_positions["BABA"])):

        if (10 - our_current_positions["BABA"] >= our_current_positions["BABZ"]):
            amount_converted = our_current_positions["BABZ"]
            our_current_positions["BABZ"] = our_current_positions["BABZ"] - amount_converted
            our_current_positions["BABA"] = amount_converted + our_current_positions["BABA"]
        else:
            amount_converted = 10 - our_current_positions["BABA"]
            our_current_positions["BABZ"] = our_current_positions["BABZ"] - amount_converted
            our_current_positions["BABA"] = amount_converted + our_current_positions["BABA"]

        convert_position(exchange, wait_time, "BABZ", amount_converted, "SELL")

    XLK = our_current_positions["XLK"] % 10
    BOND = our_current_positions["BOND"] % 3
    APPL = our_current_positions["AAPL"] % 2
    MSFT = our_current_positions["MSFT"] % 3
    GOOG = our_current_positions["GOOG"] % 2


    if (market_price["XLK"] * (our_current_positions["XLK"] % 10) + 98< market_price["EXXLK"] * (our_current_positions["XLK"] % 10)):
        if (min(33 - BOND, 50 - APPL, 33 - MSFT, 50 - GOOG) >= XLK):
            amount_converted = XLK
            our_current_positions["XLK"] -= 10 * amount_converted
            our_current_positions["BOND"] += 3 * amount_converted
            our_current_positions["AAPL"] += 2 * amount_converted
            our_current_positions["MSFT"] += 3 * amount_converted
            our_current_positions["GOOG"] += 2 * amount_converted
        else:
            amount_converted = min(33 - BOND, 50 - APPL, 33 - MSFT, 50 - GOOG)
            our_current_positions["XLK"] -= 10 * amount_converted
            our_current_positions["BOND"] += 3 * amount_converted
            our_current_positions["AAPL"] += 2 * amount_converted
            our_current_positions["MSFT"] += 3 * amount_converted
            our_current_positions["GOOG"] += 2 * amount_converted


        convert_position(exchange, wait_time, "XLK", amount_converted, "SELL")


    if (market_price["XLK"] * (our_current_positions["XLK"] % 10) > 98 + market_price["EXXLK"] * (our_current_positions["XLK"] % 10)):
        if (10 - (XLK) >= min(BOND, APPL, MSFT, GOOG)):
            amount_converted = min(BOND, APPL, MSFT, GOOG)
            our_current_positions["XLK"] += 10 * amount_converted
            our_current_positions["BOND"] -= 3 * amount_converted
            our_current_positions["AAPL"] -= 2 * amount_converted
            our_current_positions["MSFT"] -= 3 * amount_converted
            our_current_positions["GOOG"] -= 2 * amount_converted
        else:
            amount_converted = 10 - (XLK)
            our_current_positions["XLK"] += 10 * amount_converted
            our_current_positions["BOND"] -= 3 * amount_converted
            our_current_positions["AAPL"] -= 2 * amount_converted
            our_current_positions["MSFT"] -= 3 * amount_converted
            our_current_positions["GOOG"] -= 2 * amount_converted


        convert_position(exchange, wait_time, "XLK", amount_converted, "BUY")



# ~~~~~============== MAIN LOOP ==============~~~~~


def main(wait_time, exchange):
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!


    # We need to read the messages and do stuff accordingly
    rand = random.randint(0,100000000)
    messages = read_from_exchange(exchange)

    read_message(messages)
    update_market_price()
    for symbol in market_price.keys():
        buysell(exchange, symbol, rand)
    converting(exchange, rand)

    time.sleep(.8)

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
        wait_time = time.time() - start_time
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
