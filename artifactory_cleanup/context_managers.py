from contextlib import contextmanager
from teamcity import is_running_under_teamcity
from teamcity.messages import TeamcityServiceMessages

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


def get_context_managers():
    if is_running_under_teamcity():
        TC = TeamcityServiceMessages()
        ctx_mgr_block = TC.block
        ctx_mgr_test = TC.test
    else:
        ctx_mgr_block = block
        ctx_mgr_test = test
    return ctx_mgr_block, ctx_mgr_test
