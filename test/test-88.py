#!/usr/bin/env python


class Test:
    def __init__(self, url):
        self.port = 8000
        self.url = url + ':{}'.format(self.port)

test = Test("1.2.3.4")
