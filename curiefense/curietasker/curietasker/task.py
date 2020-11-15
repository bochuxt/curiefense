import datetime
import threading
import logging
import time
from . import exceptions

ONE_MINUTE = datetime.timedelta(minutes=1)



def time_match(d, datespec):
    for spec in ["year", "month", "day", "dayofweek", "hour", "minute"]:
        if spec in datespec:
            val = datespec[spec]
            target = getattr(d,spec)
            if type(val) is str and val.startswith("*/"):
                val = int(val[2:])
                if target % val != 0:
                    return False
            else:
                if int(val) != target:
                    return False
    return True


class Task(object):
    types = {}
    @classmethod
    def register(cls, name):
        def reg(t, cls=cls, name=name):
            cls.types[name] = t
            return t
        return reg
    @classmethod
    def get_task_class(cls, name):
        return cls.types[name]

    def __init__(self, options, taskid, name, datespec, **args):
        self.options = options
        self.confserver = options.api
        self.log = logging.getLogger(f"curietasker:task:[{taskid}]")
        self.taskid = taskid
        self.name = name
        self.datespec = datespec
        self.thread = None
        try:
            self.check_args(**args)
        except TypeError as e:
            raise exceptions.TaskArgumentError(f"[{name}] ({taskid}): {e}")

    def check_args(self, **args):
        self.log.debug(f"Unused args: {args}")

    def run_if_needed(self, start_timemark, stop_timemark):
        current = start_timemark
        while current <= stop_timemark:
            if time_match(current, self.datespec):
                self.thread = threading.Thread(target=self.guarded_action, args=())
                self.thread.start()
                self.start_time = datetime.datetime.now() 
                self.thread_id = self.thread.ident
                return True
            current += ONE_MINUTE
        return False
    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()
    def join(self, timeout=None):
        return self.thread is not None and self.thread.join(timeout)
    def thread_id(self):
        if self.thread is not None:
            return self.thread.get_ident()
    def guarded_action(self):
        try:
            self.action()
        except Exception as e:
            self.log.exception(f"task [{self.name}] started at {self.start_time} id {self.thread_id} action error: {e}")

    def action(self):
        pass

