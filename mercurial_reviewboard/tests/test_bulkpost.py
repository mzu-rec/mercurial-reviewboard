from mock import patch
from nose.tools import eq_

from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

@patch('mercurial_reviewboard.send_review')
def test_bulkpost(mock_send):
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    opts['bulkpost'] = True
    opts['parent'] = '000000'
    postreview(ui, repo, **opts)
    
    expected0 = open('mercurial_reviewboard/tests/diffs/two_revs_0', 'r').read()
    eq_(expected0, mock_send.call_args_list[0][0][4])
    expected1 = open('mercurial_reviewboard/tests/diffs/two_revs_1', 'r').read()
    eq_(expected1, mock_send.call_args_list[1][0][4])