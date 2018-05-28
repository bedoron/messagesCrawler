import json
import sys
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from datetime import datetime
import conversation_finder
import urllib
import os

MONTH_INCREMENT = relativedelta(months=1)  # datetime + this


def load_settings():
    with open('settings.json', 'r') as f:
        settings = json.load(f)
        return settings['username'], settings['password'], settings['starting_date'], settings['first_name'], settings[
            'last_name']


user_name, password, starting_date, first_name, last_name = load_settings()
MESSAGE_TIME = datetime.strptime(starting_date, "%d/%m/%Y")


def get_epoch_millis(the_datetime):
    return int((the_datetime - datetime(1970, 1, 1)).total_seconds())


MESSAGE_URL = "https://mobile.facebook.com/messages/read/?tid={thread_id}&start={messages}&last_message_timestamp={timestamp}"

target_folder = "cap_" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
target_dir = os.path.join(os.getcwd(), target_folder)

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

print "Created screenshot dirs: " + target_dir

driver = webdriver.Chrome()
# driver = webdriver.Firefox()

driver.get("https://www.facebook.com/messages/t/annde3")

# Login
email = driver.find_element_by_id("email")
email.send_keys(user_name)

passwd = driver.find_element_by_id("pass")
passwd.send_keys(password)

submit_button = driver.find_element_by_id("loginbutton")
submit_button.click()

src = driver.page_source
(thread_id, message_count) = conversation_finder.get_conversation_id(src, first_name, last_name)

if thread_id is None:
    print "Conversation wasn't found"
    sys.exit(-1)


# DONE WITH LOGIN

def month_iterator(starting_time):
    current_date = starting_time
    while get_epoch_millis(current_date) < get_epoch_millis(datetime.today()):
        yield get_epoch_millis(current_date)
        current_date = current_date + MONTH_INCREMENT


def calculate_file_name(screenshot_timestamp, target_dir):
    screenshot_date = datetime.fromtimestamp(int(screenshot_timestamp))
    target_file_name = "cap_" + screenshot_date.strftime('%Y-%m-%d_%H-%M-%S') + ".jpg"
    return os.path.join(target_dir, target_file_name)


encoded_thread_id = urllib.quote(thread_id)
for chat_month in month_iterator(MESSAGE_TIME):
    message_url = MESSAGE_URL.format(messages=message_count, timestamp=chat_month, thread_id=encoded_thread_id)
    calculate_file_name(chat_month, target_dir)
    driver.get(message_url)
    target_file = calculate_file_name(chat_month, target_dir)
    print "Snipping", target_file
    driver.get_screenshot_as_file(target_file)

raw_input("Waiting to be done...")
driver.close()
