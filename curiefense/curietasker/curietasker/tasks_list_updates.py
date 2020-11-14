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
        assert type(list_ids) is list or list_ids == "*", f"Unrecognized list ids: {list_ids!r}"
        assert type(branches) is list or branches == "*", f"Unrecognized branch list: {branches!r}"
        self.list_ids = list_ids
        self.branches = branches
    def action(self):

        branches = self.branches
        if branches == "*":
            l = self.confserver.configs.list().body
            branches = [ b["id"] for b in l ]
            self.log.info(f"Working on all branches: {branches!r}")
        for branch in branches:
            lstids = self.list_ids
            if lstids == "*":
                lstids = self.confserver.entries.list(branch, "profilinglists").body
                self.log.info(f"Working on lists: {lstids!r}")
            for lstid in lstids:
                self.log.info(f"Downloading {lstid} in branch {branch}")
                try:
                    lst = self.confserver.entries.get(branch, "profilinglists", 
                                                      lstid).body
                except Exception as e:
                    self.log.error(f"Could not download {lstid} in branch {branch}: {e}")
                    continue
                source = lst.get("source")
                if source == "self-managed":
                    self.log.info(f"List {lstid} is self-managed")
                    continue

                self.log.info(f"Downloading update from {source}")
                try:
                    r = requests.get(source)
                    r.raise_for_status()
                except Exception as e:
                    self.log.error(f"Could not download url [{source}] for list {lstid}")
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
                                    self.log.error(f"Error parsing [{source}] line [{l!r}]: {e}")
                    except Exception as e:
                        self.log.error(f"Error parsing content from [{source}]: {e}")
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

