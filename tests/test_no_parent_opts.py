from mock import patch
from nose.tools import eq_

from hg_reviewboard import postreview
from tests import get_initial_opts, get_repo, mock_ui

@patch('hg_reviewboard.send_review')
def test_outgoing(mock_send):
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    postreview(ui, repo, **opts)
    
    expected = open('tests/diffs/two_revs_1', 'r').read()
    eq_(expected, mock_send.call_args[0][4])