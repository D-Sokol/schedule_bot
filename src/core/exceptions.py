class ScheduleBaseException(RuntimeError):
    pass


class ImageManagementException(ScheduleBaseException):
    pass


class ImageNotProcessedException(ImageManagementException):
    pass


class ImageContentEmpty(ImageNotProcessedException):
    pass


class DuplicateNameException(ImageManagementException):
    pass


class ImageNotExist(ImageManagementException):
    pass
