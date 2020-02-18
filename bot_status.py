import time

class Status(dict):
    def __init__(self, timeout=15, **kwargs):
        super(Status, self).__init__(kwargs)
        self.timeout = timeout
        self._start_time = time.time()
        self._end_time = time.time() + timeout
    
    def check_timeout(self):
        return time.time() >= self._end_time

    def __getattr__(self, name):
        return self[name]
