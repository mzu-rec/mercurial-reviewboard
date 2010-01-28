from mock import patch
from nose.tools import eq_

from hg_reviewboard import postreview
from tests import get_initial_opts, get_repo, mock_ui

@patch('hg_reviewboard.send_review')
def test_branch(mock_send):
    ui = mock_ui()

    repo = get_repo(ui, 'branch')
    opts = get_initial_opts()
    opts['branch'] = True
    
    postreview(ui, repo, **opts)
    
    expected = open('tests/diffs/branch', 'r').read()
    eq_(expected, mock_send.call_args[0][4])