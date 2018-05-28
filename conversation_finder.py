import json
import re

from bs4 import BeautifulSoup
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit import ast


def find_conversation(threads, target_friend_object):
    conversations = filter(lambda thread:
                           len(thread['participants']) == 2 and
                           any([target_friend_object['id'] in participant for participant in thread['participants']]),
                           threads)

    deduped_conversations = dict([[conversation['thread_id'], conversation['message_count']] for conversation in conversations])

    if deduped_conversations.items() != 1:
        print "Found more than one conversation, using first"

    return deduped_conversations.items().pop()


def get_threads(tree):
    for node in nodevisitor.visit(tree):
        if not isinstance(node, ast.Assign):
            continue

        if not (node.op == ':' and "threads" in node.left.value):
            continue

        if not isinstance(node.right, ast.Array):
            continue

        return json.loads(node.right.to_ecma())

    return None


def get_conversation_id(page_source, first_name, last_name):
    js_part = find_relevant_javascript(page_source)

    parser = Parser()
    tree = parser.parse(js_part)

    friends_list = get_friends_list(tree)

    if friends_list is None:
        print "Failed extracting friends list"
        return

    first_name = first_name.lower()
    last_name = last_name.lower()

    target_friend_object = get_target_friend_object(friends_list, first_name, last_name)

    threads = get_threads(tree)
    return find_conversation(threads, target_friend_object)


def get_target_friend_object(friends_list, first_name, last_name):
    names = []

    for friend in friends_list.values():
        current_friend_name = friend['name'].lower()
        current_friend_first_name = friend['firstName'].lower()

        names += [current_friend_name]
        if first_name in current_friend_first_name and last_name in current_friend_name:
            return friend

    print "Couldn't find friend name in: "
    print "\r\n".join(names)

    return None


def get_friends_list(tree):
    for node in nodevisitor.visit(tree):
        if not isinstance(node, ast.Assign):
            continue

        if not (node.op == ':' and "shortProfiles" in node.left.value):
            continue

        return json.loads(node.right.to_ecma())

    return None


def find_relevant_javascript(page_source):
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
