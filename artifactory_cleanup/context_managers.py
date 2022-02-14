from contextlib import contextmanager
from teamcity import is_running_under_teamcity
from teamcity.messages import TeamcityServiceMessages
import os


def is_running_under_github_actions():
    return "GITHUB_ACTIONS" in os.environ


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


@contextmanager
def github_block(name):
    """
    As TC.block use "name" as a parameter, contextlib.nullcontext() can not be
    used directly
    """
    print(f"::group::{name}")
    yield
    print("::endgroup::")


def get_context_managers():
    if is_running_under_teamcity():
        TC = TeamcityServiceMessages()
        ctx_mgr_block = TC.block
        ctx_mgr_test = TC.test
    elif is_running_under_github_actions():
        ctx_mgr_block = github_block
        ctx_mgr_test = test
    else:
        ctx_mgr_block = block
        ctx_mgr_test = test
    return ctx_mgr_block, ctx_mgr_test
