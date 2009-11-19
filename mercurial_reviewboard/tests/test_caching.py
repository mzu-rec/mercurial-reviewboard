'Test cached credentials and repository ids used during a bulk post.'

from mock import Mock, patch
from nose.tools import eq_

from mercurial_reviewboard import (expandpath, find_reviewboard_repo_id, 
                                   getreviewboard)
from mercurial_reviewboard.tests import get_initial_opts, mock_ui

@patch('mercurial_reviewboard.ReviewBoard')
def test_credentials_cache(mock_reviewboard):
    'Repeated calls to getreviewboard should yield cached credentials.'
    # original mock credentials = foo/bar
    ui = mock_ui()
    
    # remove the user credential
    ui.setconfig('reviewboard', 'user', None)
    
    # supply it via the command line instead
    ui.prompt.return_value = 'baz'
    
    getreviewboard(ui)
    
    eq_('baz', ui.config('reviewboard', 'user'), 
        'user should be cached in the ui')
    
def test_repoid_cache():
    'Repeated calls to find_reviewboard_repo_id yield a cached repoid.'
    
    reviewboard = Mock()
    
    # create a repository that will match the remotepath
    ui = mock_ui()
    opts = get_initial_opts()
    opts['outgoingrepo'] = 'foo'
    reviewboard.repositories.return_value = [{
        'path': expandpath(ui, 'foo'),
        'name': 'bar',
        'tool': 'Mercurial',
        'id': 101
    }]
    
    find_reviewboard_repo_id(ui, reviewboard, opts)
    
    eq_(101, opts.get('repoid'), 'repoid should be cached in opts')