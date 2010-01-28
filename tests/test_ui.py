from mock import Mock, patch_object
from nose.tools import eq_

import hg_reviewboard
from hg_reviewboard import postreview
from tests import get_initial_opts, get_repo, mock_ui

class TestChangesetsOutput:
    
    expected_status = \
        'changesets:\n\t1:669e757d4a24 "1"\n\t0:a8ea53640b24 "0"\n\n'

    @patch_object(hg_reviewboard, 'new_review')
    def test_changeset_shown(self, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = '000000'
        postreview(ui, repo, **opts)
        
        eq_(self.expected_status, ui.status.call_args_list[1][0][0])
        
    @patch_object(hg_reviewboard, 'update_review')
    def test_changeset_shown_on_existing(self, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = '000000'
        opts['update'] = False
        opts['existing'] = '1'
        postreview(ui, repo, **opts)
        
        eq_(self.expected_status, ui.status.call_args_list[1][0][0])
        
class TestLaunchBrowser:

    @patch_object(hg_reviewboard, 'new_review')
    @patch_object(hg_reviewboard, 'webbrowser')
    def test_browser_launch_default(self, mock_webbbrowser, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_webbbrowser.open.called == False
        
    @patch_object(hg_reviewboard, 'new_review')
    @patch_object(hg_reviewboard, 'webbrowser')
    def test_browser_launch_false(self, mock_webbbrowser, mock_create_method):
        ui = mock_ui()
        ui.setconfig('reviewboard', 'launch_webbrowser', 'false')
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_webbbrowser.open.called == False
        
    @patch_object(hg_reviewboard, 'new_review')
    @patch_object(hg_reviewboard, 'webbrowser')
    def test_browser_launch_true(self, mock_webbbrowser, mock_create_method):
        ui = mock_ui()
        ui.setconfig('reviewboard', 'launch_webbrowser', 'true')
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_webbbrowser.open.called
        