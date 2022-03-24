# -*- coding: utf-8 -*-
from __future__ import unicode_literals 
from flask import Flask, request

from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
import telegram

import time, sys, json, pytz
from datetime import datetime, timedelta

from constants import *
from GoogleSheets import googleSheets

# todo: add check that message passed and spreadsheet updated
#       1. We firstly go to spreadsheet and only then to telegram
# todo: Working time: on exit time - last time if it is enter
#       1.
# todo: /setinlinegeo - toggle inline location requests (https://core.telegram.org/bots/inline#location-based-results)
#       1.
# todo: Check uWSGI workers requests distribution
#       1.
# todo: empty name/surname, username check and fullname correct creation
# todo: check errors for res = json (drive calls and telegram calls)
# todo: if check in is 01/01/2020 23:00 and check out 02/01/2020 01:00, then send three messages:
# 01/01/2020 23:59:59 check out
# 02/01/2020 00:00:01 check in
# 02/01/2020 01:00:00 check out




app = Flask(__name__)
app.debug = True

global bot
bot = telegram.Bot(token=TOKEN)

def checkUserIsWorking(uid):
    """
    Checks that user already works
    :param uid: user id
    :return: True if user busy, False o.w.
    """
    openAccounts = {}

    with open("accounts/openAccounts.json", "r") as json_file:
        openAccounts = json.load(json_file)
        json_file.close()

    if(str(uid) in openAccounts.keys()):
        return True
    else:
        return False

def updateWorkStatus(uid, new_status):
    """
    Updates users work status
    :param uid: user id
    :param new_status:
    :return: deletes uid from work status file if new_status == "Not working",
             adds uid to work status file if new_status == "Not working"
    """
    openAccounts = {}

    with open("accounts/openAccounts.json", "r") as json_file:
        openAccounts = json.load(json_file)
        json_file.close()


    if(str(uid) in openAccounts.keys()):
        if(new_status=="Not working"):
            del openAccounts[str(uid)]
        else:
            print(f"WORK STATUS ERROR: uid: {uid}, new status: {new_status}")
    else:
        if(new_status=="Working"):
            openAccounts[str(uid)]=""
        else:
            print(f"\nWORK STATUS ERROR: uid: {uid}, new status: {new_status}\n")

    with open("accounts/openAccounts.json", "w") as json_file:
        json.dump(openAccounts, json_file)
        json_file.close()

#todo: Check location by message
def checkLocation():
    pass

def getMessageData(message):
    """
    :param message: update.message object
    :return: dictionary of message parameters
    """
    msgData = {}
    msgData['chat_id']  = message.chat.id
    msgData['msg_time'] = message.date
    msgData['text'] = message.text
    print(f"chat_id: {msgData['chat_id']}\ndate: {msgData['msg_time']}\ntext: {msgData['text']}")

    msgData['uid'] = message.from_user.id
    msgData['uname'] = message.from_user.username

    msgData['location'] = message.location
    msgData['full_name'] = str(message.from_user.first_name) + " " + str(message.from_user.last_name)
    return msgData

def getLocalTime(UTC_time):
    """
    Transforms message time to local timezone
    :param UTC_time: message datetime in UTC timezone
    :return: local date and time
    """
    local_tz = pytz.timezone('Asia/Jerusalem')
    local_datetime = UTC_time.replace(tzinfo=pytz.utc).astimezone(local_tz)

    datetime_list = str(local_datetime.date()).split('-')

    local_date = datetime_list[2] + '/' + datetime_list[1] + '/' + datetime_list[0]
    local_time = str(local_datetime.time())
    return local_date, local_time

def locToLatLong(location):
    """
    :param location: location in string format
    :return: latitude and longtitude in float format
    """
    long, lat = str(location).split(',')
    long = float(long.split(':')[-1])
    lat = float(lat.split(':')[-1][:-1])
    return lat, long

gs = googleSheets(google_credentials)

#WebHook
@app.route('/HOOK', methods=['POST', 'GET'])
def webhook_handler():
    print("\n ==== hook update ==== ")
    if request.method == "POST":
        kb = ReplyKeyboardMarkup([["Start job"],["Job done"],])
        print(f"TIME: {time.time()}")
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if(update.message!=None):
            try:
                msgData = getMessageData(update.message)                # message data
                m_date, m_time = getLocalTime(msgData['msg_time'])      # message local date and time
                ws_name = f"{msgData['full_name']}_{msgData['uid']}"    # user worksheet name
                location = msgData['location']                          # location from message
                # If location != None - user enters work
                if(location!= None):
                    if(checkUserIsWorking(msgData['uid'])):
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job already started", reply_markup=kb)
                    else:
                        lat, long = locToLatLong(location)
                        args = [m_date, m_time, msgData['uid'], msgData['uname'], msgData['full_name'], 'IN', lat, long ]
                        print(f"USER IN:\n {args}")
                        # add data to spreadsheet
                        gs.add_checkInOut(ws_name, args)
                        # send response to telegram
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job started", reply_markup=kb)
                        # update work status in openAccountsfile
                        updateWorkStatus(msgData['uid'],"Working")

                # If user presses button "Start job" - he start new job
                elif (msgData['text'] == 'Start job'):
                    if (checkUserIsWorking(msgData['uid'])):
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job already started", reply_markup=kb)
                    else:
                        args = [m_date, m_time, msgData['uid'], msgData['uname'], msgData['full_name'], 'IN', "", ""]
                        print(f"USER IN:\n {args}")
                        # add data to spreadsheet
                        gs.add_checkInOut(ws_name, args)
                        # send response to telegram
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job started", reply_markup=kb)
                        # update work status in openAccountsfile
                        updateWorkStatus(msgData['uid'], "Working")

                # Only other option is exit
                elif(msgData['text'] == 'Job done'):
                    if (checkUserIsWorking(msgData['uid'])):
                        args = [m_date, m_time, msgData['uid'], msgData['uname'], msgData['full_name'], 'OUT',"",""]
                        print(f"USER OUT:\n {args}")
                        # add data to spreadsheet
                        gs.add_checkInOut(ws_name, args)
                        # send response to telegram
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job finished", reply_markup=kb)
                        # update work status in openAccountsfile
                        updateWorkStatus(msgData['uid'], "Not working")
                    else:
                        bot.send_message(chat_id=msgData['chat_id'], text=f"Job wasn't started", reply_markup=kb)
            except:
                print("Unexpected error:", sys.exc_info()[0])
                raise
        else:
            print("Empty update")
    return 'ok'

#Set_webhook
@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://%s:443/HOOK' % URL, certificate=open(f'/etc/ssl/{username}/server.crt', 'rb'))
    if s:
        print(s)
        return "webhook setup ok"
    else:
        return "webhook setup failed"

@app.route('/')
def index():
    return '<h1>ROCK!</h1>'