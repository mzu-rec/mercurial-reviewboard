from mock import patch
from nose.tools import eq_

from hg_reviewboard import postreview
from tests import get_initial_opts, get_repo, mock_ui

@patch('hg_reviewboard.send_review')
def test_outgoing(mock_send):
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    opts['outgoingrepo'] = 'tests/repos/no_revs'
    opts['outgoingchanges'] = True
    postreview(ui, repo, **opts)
    
    expected = open('tests/diffs/outgoing', 'r').read()
    eq_(expected, mock_send.call_args[0][4])
    
@patch('hg_reviewboard.send_review')
def test_outgoing_with_branch(mock_send):
    '''Test that only one change is included, despite a commit to another 
    branch.'''
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs_clone')
    opts = get_initial_opts()
    opts['outgoingrepo'] = 'tests/repos/two_revs'
    opts['outgoingchanges'] = True
    postreview(ui, repo, '2', **opts)
    
    expected = open('tests/diffs/outgoing_with_branch', 
                    'r').read()
    eq_(expected, mock_send.call_args[0][4])