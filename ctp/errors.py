# This error is an expected user error message and it will be caught
# and printed without a stacktrace
class CTPError (RuntimeError):
    pass
