from nose.tools import eq_

from hg_reviewboard import find_reviewboard_repo_id
from tests import get_initial_opts

def test_repo_id_from_opts():
    opts = get_initial_opts()
    opts['repoid'] = '101'
    eq_(101, find_reviewboard_repo_id(None, None, opts))