from datetime import datetime


def mockable_current_datetime():
    return datetime.now()


def current_datetime():
    # get datetime.now() or mocked datetime in testing
    return mockable_current_datetime()
