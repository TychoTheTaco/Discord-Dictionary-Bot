class InsufficientPermissionsException(BaseException):

    def __init__(self, permissions):
        self._permissions = permissions

    @property
    def permissions(self):
        return self._permissions
