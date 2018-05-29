import json
import urllib

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC

from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit import ast


class FriendsList(object):
    def __init__(self, page_source):
        super(FriendsList, self).__init__()
        js_part = FriendsList._lookup_initial_chat_friends_list(page_source)
        parser = Parser()
        self._tree = parser.parse(js_part)
        self._friends_list = FriendsList._get_friends_list(self._tree)
        self._threads = FriendsList._get_threads(self._tree)

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

            if not (node.op == ':' and "threads" in node.left.value):
                continue

            if not isinstance(node.right, ast.Array):
                continue

            return json.loads(node.right.to_ecma())

        return None

    def _get_target_friend_object(self, first_name, last_name):
        names = []
        for friend in self._friends_list.values():
            current_friend_name = friend['name'].lower()
            current_friend_first_name = friend['firstName'].lower()

            names += [current_friend_name]
            if first_name in current_friend_first_name and last_name in current_friend_name:
                return friend

        print "Couldn't find friend name in: "
        print "\r\n".join(names)

        return None

    def get_conversation(self, first_name, last_name):
        first_name = first_name.lower()
        last_name = last_name.lower()

        target_friend_object = self._get_target_friend_object(first_name, last_name)

        conversations = filter(lambda thread:
                               len(thread['participants']) == 2 and
                               any([target_friend_object['id'] in participant for participant in
                                    thread['participants']]),
                               self._threads)

        deduped_conversations = dict(
            [[conversation['thread_id'], conversation['message_count']] for conversation in conversations])

        if deduped_conversations.items() != 1:
            print "Found more than one conversation, using last"

        conversation = deduped_conversations.items().pop()

        return Conversation(conversation[0], conversation[1])


class Conversation(object):
    def __init__(self, thread_id, message_count):
        super(Conversation, self).__init__()
        self._thread_id = thread_id
        self._encoded_thread_id = urllib.quote(thread_id)
        self._message_count = message_count

    def __iter__(self):
        pass


class FBModel(object):
    def __init__(self, driver, target_url):
        super(FBModel, self).__init__()
        self._driver = driver
        self._target_url = target_url
        self._login_success = False

    def do_login(self):
        self._driver.get(self._target_url)
        self._driver.implicitly_wait(2)
        title = self._driver.title
        wait(self._driver, 120).until_not(EC.title_is(title))
        self._login_success = 'messenger' in self._driver.title.lower()
        return self._login_success


if __name__ == "__main__":
    driver = webdriver.Chrome()

    success = FBModel(driver, "https://www.facebook.com/messages/t/annde3").do_login()
    print success

    driver.close()
