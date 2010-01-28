from mock import patch

from hg_reviewboard import getreviewboard
from tests import get_initial_opts, mock_ui

@patch('hg_reviewboard.ReviewBoard')
def test_get_credentials_from_config(mock_reviewboard):
        
    # username and password configs are included 
    # in the mock
    ui = mock_ui()
    opts = get_initial_opts()
        
    getreviewboard(ui, opts)
    
    mock_reviewboard.return_value.login.assert_called_with('foo', 'bar')

    