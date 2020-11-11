import time
import datetime
import logging
import json

from .task import Task
from . import tasks_list_updates
from .exceptions import *

log = logging.getLogger("curietasker")

ONE_MINUTE = datetime.timedelta(minutes=1)

def get_tasks(options):
    try:
        if options.task_file is None:
            tasks = options.api.db.get(options.task_db_name).body
        else:
            tasks = json.load(options.task_file)
    except Exception as e:
        if options.task_file is None:
            err = f"Could not retrieve taskdb [{options.task_db_name}] at {options.base_url}"
        else:
            err = f"Could not parse content of file {options.task_file}"
        raise TaskListNotFound(f"{err}: {e}")
    return tasks

def get_task(options, taskid):
    tasks = get_tasks(options)
    for t in tasks["tasklist"]:
        if t["id"] == taskid:
            return t
    else:
        raise TaskNotFound(f"Task not found ({taskid})")

def create_task(options, jtask):
    tid = jtask.get("id")
    if not tid:
        raise TaskerInvalidTaskDescription(f"missing task id {task!r}")
    name = jtask.get("name")
    if not name:
        raise TaskerInvalidTaskDescription(f"task ({tid}): missing task name")
    kind = jtask.get("kind")
    if not kind:
        raise TaskerInvalidTaskDescription(f"task [{name}] ({tid}): missing 'kind' attribute")
    try:
        T = Task.get_task_class(kind)
    except KeyError:
        raise TaskerInvalidTaskDescription(f"task [{name}] ({tid}): unkown task kind: {kind!r}")
    datespec = jtask.get("datespec")
    if not kind:
        raise TaskerInvalidTaskDescription(f"task [{name}] ({tid}): missing 'datespec' attribute")

    task = T(options, taskid=tid, name=name, datespec=datespec, **jtask.get("args",{}))

    return task



def tasker(options):
    log = logging.getLogger("curietasker:tasker")
    while True:

        next_timemark = datetime.datetime.now().replace(second=0, microsecond=0)+ONE_MINUTE
        while True:
            now = datetime.datetime.now()
            if now > next_timemark:
                break
            slp = (next_timemark-now).total_seconds()
            log.info(f"----- Sleeping {slp} seconds to {next_timemark}  -----")
            time.sleep(slp)
        log.info(f"##### Processing from {options.timemark} to {next_timemark}  #####")
        tasks = get_tasks(options)

        for jtask in tasks["tasklist"]:
            try:
                task = create_task(options, jtask)
            except TaskerException as e:
                log.error(e)
                if options.debug:
                    log.exception(e)
            else:
                if task.run_if_needed(options.timemark, next_timemark):
                    options.tasklist.add(task)
                    log.info(f"==> Task [{task.name}] started at {task.start_time}.")

        for task in list(options.tasklist):
            if not task.is_alive():
                log.info(f"<== Task [{task.name}] finished (was started at {task.start_time}).")
                task.join()
                options.tasklist.remove(task)
            else:
                log.info(f"STATUS: Task [{task.name}] still running (was started at {task.start_time}.")
        log.info(f"STATUS: {len(options.tasklist)} tasks still running")
        options.timemark = next_timemark

def start(options):
    options.tasklist = set()
    while True:
        try:
            tasker(options)
        except KeyboardInterrupt:
            log.info(f"Stopped by user. Waiting for {len(options.tasklist)} tasks to finish.")
            for task in options.tasklist:
                task.join()
            log.info(f"All tasks finished.")
            return
        except Exception as e:
            log.exception(f"tasker: {e}")
            time.sleep(1)


def runtask(options):
    try:
        jtask = get_task(options, options.taskid)
        task = create_task(options, jtask)
    except Exception as e:
        log.error(e)
        if options.debug:
            log.exception(e)
    else:
        log.info(f"Starting task [{task.name}]")
        task.action()
        log.info(f"Task [{task.name}] finished")
