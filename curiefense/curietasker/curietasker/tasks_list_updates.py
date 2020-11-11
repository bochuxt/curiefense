import time
import datetime
import requests
import json
import re

from .task import Task

@Task.register("update")
class TaskUpdate(Task):
    parsers = {
        "ip": re.compile("^(?P<val>(([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})|(([0-9a-f]*:+){1,8}))(/[0-9]{1,2})) *([;#] *(?P<comment>.*$))?", re.IGNORECASE),
        "asn": re.compile("^as(?P<val>[0-9]{3,6}) *([;#] *(?P<comment>.*$))?", re.IGNORECASE),
    }
    def check_args(self, list_ids, branches):
        assert type(list_ids) is list, f"Unrecognized list ids: {list_ids!r}"
        assert type(branches) is list, f"Unrecognized branch list: {branches!r}"
        self.list_ids = list_ids
        self.branches = branches
    def action(self):
        for lstid in self.list_ids:
            for branch in self.branches:
                self.log.info(f"Downloading {lstid} in branch {branch}")
                try:
                    lst = self.confserver.entries.get(branch, "profilinglists", 
                                                      lstid).body
                except Exception as e:
                    self.log.error(f"Could not download {lstid} in branch {branch}: {e}")
                    continue
                if "source" not in lst:
                    self.log.error(f"Profiling list {lstid} is missing 'source' attribute")
                    continue

                self.log.info(f"Downloading update from {lst['source']}")
                try:
                    r = requests.get(lst["source"])
                    r.raise_for_status()
                except Exception as e:
                    self.log.error(f"Could not download url [{lst['source']}] for list {lstid}")
                    continue

                lst["mdate"] = datetime.datetime.now().isoformat()
                entries = []
                try:
                    entries = json.loads(r.text)
                except json.decoder.JSONDecodeError:
                    try:
                        for l in r.text.splitlines():
                            for label,regexp in self.parsers.items():
                                try:
                                    m = regexp.match(l)
                                    if m:
                                        entries.append([ label, m.group("val"), 
                                                         m.group("comment") or "" ])
                                        break
                                except Exception as e:
                                    self.log.error(f"Error parsing [{lst['source']}] line [{l!r}]: {e}")
                    except Exception as e:
                        self.log.error(f"Error parsing content from [{lst['source']}]: {e}")
                    self.log.info(f"Got {len(entries)} entries out of {len(r.text.splitlines())}")

                lst["entries"] = entries
                self.confserver.entries.update(branch, "profilinglists",
                                               lstid, body=lst)
                self.log.info(f"Updated {lstid} in branch {branch}")




@Task.register("publish")
class TaskPublish(Task):
    def check_args(self, branch):
        self.branch = branch
    def action(self):
        self.log.info(f"I should publish branch {self.branch}")
        time.sleep(20)
        self.log.info(f"I published {self.branch}, didn't I?")


@Task.register("update_and_publish")
class TaskUpdateAndPublish(TaskUpdate, TaskPublish):
    def check_args(self, url, branch):
        TaskUpdate.check_args(self, url)
        TaskPublish.check_args(self, branch)
    def action(self):
        TaskUpdate.action(self)
        TaskPublish.action(self)

