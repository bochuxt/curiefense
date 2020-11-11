class TaskerException(Exception):
    pass

class TaskListNotFound(TaskerException):
    pass

class TaskNotFound(TaskerException):
    pass

class TaskerInvalidTaskDescription(TaskerException):
    pass


class TaskArgumentError(TaskerException):
    pass
