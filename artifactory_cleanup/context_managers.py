from contextlib import contextmanager


@contextmanager
def block(name):
    """
    As TC.block use "name" as a parameter, contextlib.nullcontext() can not be
    used directly
    """
    yield


@contextmanager
def test(testName):
    """
    As TC.test use "testName" as a parameter, contextlib.suppress() can not be
    used directly
    """
    yield
