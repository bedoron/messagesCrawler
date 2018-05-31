import json
import urllib
from datetime import datetime

import os
from dateutil.relativedelta import relativedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC

from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit import ast


class FriendsList(object):
    def __init__(self, friends_list_js):
        super(FriendsList, self).__init__()
        parser = Parser()
        self._tree = parser.parse(friends_list_js)
        self._friends_list = FriendsList._get_friends_list(self._tree)
        self._threads = FriendsList._get_threads(self._tree)

    @staticmethod
    def from_source(page_source):
        """
        :rtype: FriendsList
        """
        friends_list_js = FriendsList._lookup_initial_chat_friends_list(page_source)
        return FriendsList(friends_list_js)

    @staticmethod
    def _lookup_initial_chat_friends_list(page_source):
        soup = BeautifulSoup(page_source, 'html.parser')
        for script_tag in soup.find_all('script'):
            if len(script_tag.contents) == 0:
                continue

            script_content = script_tag.contents[0]
            if '"InitialChatFriendsList"' in script_content:
                print "Found the tag that has the initial friends list"
                return script_content

        print "Couldn't find InitialChatFriendList, API might have changed"
        return None

    @staticmethod
    def _get_friends_list(tree):
        for node in nodevisitor.visit(tree):
            if not isinstance(node, ast.Assign):
                continue

            if not (node.op == ':' and "shortProfiles" in node.left.value):
                continue

            return json.loads(node.right.to_ecma())

        return None

    @staticmethod
    def _get_threads(tree):
        for node in nodevisitor.visit(tree):
            if not isinstance(node, ast.Assign):
                continue

            if not (node.op == ':' and "thread_list" in node.left.value):
                continue

            if not isinstance(node.right, ast.Object):
                continue

            thread_list = json.loads(node.right.to_ecma())
            return thread_list.get('viewer', {}).get('message_threads', {}).get('nodes')

        return None

    def _get_target_friend_object(self, first_name, last_name):
        lookup_friend = first_name.lower() + " " + last_name.lower()
        names = []
        for friend in self._friends_list.values():
            friend_name = friend['name'].lower()
            if lookup_friend == friend_name:
                return friend

            names.append(friend_name)

        print "Couldn't find friend name in: "
        print "\r\n".join(names)

        return None

    def get_conversation(self, first_name, last_name):
        """
        :rtype: Conversation
        """
        first_name = first_name.lower()
        last_name = last_name.lower()

        target_friend_object = self._get_target_friend_object(first_name, last_name)

        for thread in self._threads:
            participants_nodes = thread['all_participants']['nodes']
            if len(participants_nodes) != 2:
                continue

            participants_to_ids = map(lambda node: node['messaging_actor']['id'], participants_nodes)
            if target_friend_object['id'] in participants_to_ids:
                return Conversation(thread)

        return None


class Conversation(object):
    MONTH_INCREMENT = relativedelta(months=1)
    CONVERSATION_URL = "https://mobile.facebook.com/messages/read/?tid={thread_id}&start={" \
                       "messages}&last_message_timestamp={timestamp} "

    def __init__(self, thread):
        super(Conversation, self).__init__()
        target_user = thread['thread_key']['other_user_id']

        participants_ids = map(lambda node: node['messaging_actor']['id'], thread['all_participants']['nodes'])
        owner_id = [participant_id for participant_id in participants_ids if participant_id != target_user][0]

        self._thread_id = 'cid.c.' + owner_id + ":" + target_user
        self._encoded_thread_id = urllib.quote(self._thread_id)
        self._message_count = thread['messages_count']

    def starting_from(self, start_date):
        current_date = start_date
        while Conversation._get_epoch_millis(current_date) < Conversation._get_epoch_millis(datetime.today()):
            yield self._get_conversation_url(current_date)
            current_date = current_date + Conversation.MONTH_INCREMENT

    def _get_conversation_url(self, date):
        date_epoch_millis = Conversation._get_epoch_millis(date)
        return date_epoch_millis, Conversation.CONVERSATION_URL.format(
            messages=self._message_count, timestamp=date_epoch_millis, thread_id=self._encoded_thread_id)

    @staticmethod
    def _get_epoch_millis(the_datetime):
        return int((the_datetime - datetime(1970, 1, 1)).total_seconds())


class FBModel(object):
    MESSAGES_PAGE = "https://www.facebook.com/messages/"

    def __init__(self, driver):
        super(FBModel, self).__init__()
        self._driver = driver
        self._login_success = False
        self._friends_list = None
        self._target_folder = "cap_" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self._target_dir = os.path.join(os.getcwd(), self._target_folder)
        if not os.path.exists(self._target_dir):
            os.makedirs(self._target_dir)

    def do_login(self):
        self._driver.get(FBModel.MESSAGES_PAGE)
        self._driver.implicitly_wait(2)
        title = self._driver.title
        wait(self._driver, 120).until_not(EC.title_is(title))
        self._login_success = 'messenger' in self._driver.title.lower()
        return self._login_success

    def get_friends_list(self):
        if not self._login_success:
            return None

        self._friends_list = FriendsList.from_source(self._driver.page_source)
        return self._friends_list

    def run(self, first_name, last_name, starting_date):
        self.do_login()
        friends_list = self.get_friends_list()

        if friends_list is None:
            print "Failed loading friends list"
            return None

        self._handle_conversation(friends_list.get_conversation(first_name, last_name), starting_date)

    def _handle_conversation(self, conversation, starting_date):
        for ts, conversation_url in conversation.starting_from(datetime.strptime(starting_date, "%d/%m/%Y")):
            self._driver.get(conversation_url)
            target_file = self._calculate_file_name(ts)
            self._driver.get_screenshot_as_file(target_file)

    def _calculate_file_name(self, screenshot_timestamp):
        screenshot_date = datetime.fromtimestamp(int(screenshot_timestamp))
        target_file_name = "cap_" + screenshot_date.strftime('%Y-%m-%d_%H-%M-%S') + ".jpg"
        return os.path.join(self._target_dir, target_file_name)


if __name__ == "__main__":
    driver = webdriver.Chrome()
    try:
        FBModel(driver).run("", "", "01/01/2015")
    finally:
        driver.close()
