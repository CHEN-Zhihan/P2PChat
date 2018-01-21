import apitest
import time


class Test(object):
    def __init__(self):
        def update(s):
            self.notify(s)
        apitest.set_callback(update)

    def notify(self, string):
        print(string)


t = Test()
