from selenium import webdriver


class FBModel(object):
    def __init__(self, target_url):
        super(FBModel, self).__init__()
        self._driver = webdriver.Chrome()
        # driver = webdriver.Firefox()
        self._target_url = target_url

    def do_login(self):
        self._driver.get(self._target_url)
        self._driver.implicitly_wait(2)
        self._driver.execute_async_script('alert("LOGIN")')
        self._driver.implicitly_wait()




if __name__ == "__main__":
    FBModel("https://www.facebook.com/messages/t/annde3").do_login()