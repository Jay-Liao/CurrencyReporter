#!/usr/bin/python
# coding=utf-8

import requests
import datetime
import urllib2
from bs4 import BeautifulSoup
from retrying import retry
import ConfigParser
import os
import smtplib
import schedule
import time


@retry(stop_max_attempt_number=5, wait_fixed=1000)
def get_sell_spot():
    content = urllib2.urlopen(
        'https://ebank.taipeifubon.com.tw/B2C/cfhqu/cfhqu009/CFHQU009_Home.faces?menuId=CFH0201&showLogin=true&popupMode=true&popupMode=true&frameMode=false&frameMode=false').read()
    # print content
    soup = BeautifulSoup(content, 'lxml')

    # structure of USD currency
    # <tr>
    # <td class="hd" rowspan="2">幣別</td>
    # <td class="hd" colspan="2">即期</td> (buySpot / sellSpot)
    # <td class="hd" colspan="2">現鈔</td> (buyCash / sellCash)
    # </tr>
    # <tr>
    # <td class="hd3" width="18%">銀行買入</td>
    # <td class="hd3" width="18%">銀行賣出</td>
    # <td class="hd3" width="18%">銀行買入</td>
    # <td class="hd3" width="18%">銀行賣出</td>
    # </tr>
    # <tr>
    # <td class="hd4"><span class="flag_USD">美金 (USD)</span></td>
    # <td class="rt">31.6500</td> (buySpot)
    # <td class="rt">31.7500</td> (sellSpot)
    # <td class="rt">31.4950</td> (buyCash)
    # <td class="rt">31.9050</td> (sellCash)
    # </tr>

    usd_span = soup.select('span[class="flag_USD"]')[0]
    usd_tr = usd_span.parent.parent
    sell_spot = float(usd_tr.select('td[class="rt"]')[1].text)
    return sell_spot


def post_message_to_general(message):
    web_hook_url = 'https://hooks.slack.com/services/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'
    response = requests.post(web_hook_url, json={"text": message})
    if response.status_code != 200:
        print("post message to Slack fails.")


def is_date_key_exist(date_key):
    config = ConfigParser.ConfigParser()
    config.read(MIN_SELL_SPOT_FILENAME)
    return config.has_option("min_sell_spot", date_key)


def get_min_sell_spot_by_date_key(date_key):
    config = ConfigParser.ConfigParser()
    config.read(MIN_SELL_SPOT_FILENAME)
    min_sell_spot = config.get('min_sell_spot', date_key)
    return float(min_sell_spot)


def set_min_sell_spot_with_date_key(date_key, sell_spot):
    config = ConfigParser.ConfigParser()
    config.read(MIN_SELL_SPOT_FILENAME)
    config.set("min_sell_spot", date_key, sell_spot)
    config.write(open(MIN_SELL_SPOT_FILENAME, 'wb'))


def get_email():
    config = ConfigParser.ConfigParser()
    config.read('Config.ini')
    email = config.get('notification', 'email')
    return email


def get_notify_price():
    config = ConfigParser.ConfigParser()
    config.read('Config.ini')
    notify_price = config.get('notify_price', 'notify_price')
    return float(notify_price)


def get_reporter_email():
    config = ConfigParser.ConfigParser()
    config.read('Config.ini')
    email = config.get('reporter', 'email')
    return email


def get_reporter_password():
    config = ConfigParser.ConfigParser()
    config.read('Config.ini')
    password = config.get('reporter', 'password')
    return password


def append_new_line_to_file(message, filename):
    with open(filename, 'a') as file:
        file.writelines(message + '\n')
    file.close()


def check_min_sell_spot_file():
    if not os.path.isfile(MIN_SELL_SPOT_FILENAME):
        file = open(MIN_SELL_SPOT_FILENAME, 'wb')
        file.close()
        config = ConfigParser.ConfigParser()
        config.read(MIN_SELL_SPOT_FILENAME)
        config.add_section('min_sell_spot')
        config.write(open(MIN_SELL_SPOT_FILENAME, 'wb'))


# def send_mail(to_address, the_message):
#     content = 'Subject: %s\n\n%s' % ('Currency Notification', the_message)
#     reporter_email = get_reporter_email()
#     reporter_password = get_reporter_password()
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.starttls()
#     server.login(reporter_email, reporter_password)
#     server.sendmail(reporter_email, to_address, content)
#     server.quit()


def job():
    check_min_sell_spot_file()
    current_time = datetime.datetime.now()
    current_date_string = str(current_time.strftime("%Y-%m-%d"))
    sell_spot = get_sell_spot()
    current_time_info = str(current_time.strftime("%Y-%m-%d(%a) %H:%M:%S"))
    message = current_time_info + ': ' + str(sell_spot)
    append_new_line_to_file(message, OUTPUT_FILENAME)
    if not is_date_key_exist(current_date_string):
        set_min_sell_spot_with_date_key(current_date_string, sell_spot)
        if sell_spot < SELL_SPOT_NOTIFY_PRICE:
            post_message_to_general(message)
            # send_mail(EMAIL, 'USD: ' + str(sell_spot))
    else:
        min_sell_spot_today = get_min_sell_spot_by_date_key(current_date_string)
        if sell_spot < min_sell_spot_today:
            set_min_sell_spot_with_date_key(current_date_string, sell_spot)
            if sell_spot < SELL_SPOT_NOTIFY_PRICE:
                post_message_to_general(message)
                # send_mail(EMAIL, 'USD: ' + str(sell_spot))


SELL_SPOT_NOTIFY_PRICE = get_notify_price()  # 到價提醒
OUTPUT_FILENAME = "output.txt"
MIN_SELL_SPOT_FILENAME = "MinSellSpot.txt"
schedule.every().minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
