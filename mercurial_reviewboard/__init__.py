'''post changesets to a reviewboard server'''

import os, errno, re, sys
import cStringIO
import operator

from mercurial import cmdutil, hg, ui, mdiff, patch, util, localrepo
from mercurial.i18n import _

from reviewboard import make_rbclient, ReviewBoardError


__version__ = '4.1.0'


def postreview(ui, repo, rev='.', **opts):
    '''post a changeset to a Review Board server

This command creates a new review request on a Review Board server, or updates
an existing review request, based on a changeset in the repository. If no
revision number is specified the parent revision of the working directory is
used.

By default, the diff uploaded to the server is based on the parent of the
revision to be reviewed. A different parent may be specified using the
--parent option.  Alternatively you may specify --outgoingchanges to calculate
the parent based on the outgoing changesets or --branch to choose the parent
revision of the branch.

If the parent revision is not available to the Review Board server (e.g. it
exists in your local repository but not in the one that Review Board has
access to) you must tell postreview how to determine the base revision
to use for a parent diff. The --outgoing, --outgoingrepo or --master options
may be used for this purpose. The --outgoing option is the simplest of these;
it assumes that the upstream repository specified in .hg/hgrc is the same as
the one known to Review Board. The other two options offer more control if
this is not the case.

The --outgoing option recognizes the path entries 'reviewboard', 'default-push'
and 'default' in this order of precedence. 'reviewboard' may be used if the
repository accessible to Review Board is not the upstream repository.
'''

    ui.status('postreview plugin, version %s\n' % __version__)
    
    # checks to see if the server was set
    find_server(ui, opts)
    
    check_parent_options(opts)

    c = repo.changectx(rev)

    rparent = find_rparent(ui, repo, c, opts)
    ui.debug('remote parent: %s\n' % rparent)
    
    parent  = find_parent(ui, repo, c, rparent, opts)
    ui.debug('parent: %s\n' % parent)

    if parent is None:
        msg = "Unable to determine parent revision for diff. "
        if opts.get('outgoingchanges'):
            msg += _("If using -g/--outgoingchanges, make sure you have some "
                     "(type 'hg out'). Did you forget to commit ('hg st')?")
        raise util.Abort(msg)

    diff, parentdiff = create_review_data(ui, repo, c, parent, rparent)

    send_review(ui, repo, c, parent, diff, parentdiff, opts)


def find_rparent(ui, repo, c, opts):
    outgoing = opts.get('outgoing')
    outgoingrepo = opts.get('outgoingrepo')
    master = opts.get('master')

    if master:
        rparent = repo[master]
    elif outgoingrepo:
        rparent = remoteparent(ui, repo, c, upstream=outgoingrepo)
    elif outgoing:
        rparent = remoteparent(ui, repo, c)
    else:
        rparent = None
    return rparent


def find_parent(ui, repo, c, rparent, opts):
    parent = opts.get('parent')
    outgoingchanges = opts.get('outgoingchanges')
    branch = opts.get('branch')
    
    if outgoingchanges:
        parent = rparent
    elif parent:
        parent = repo[parent]
    elif branch:
        parent = find_branch_parent(ui, c)
    else:
        parent = c.parents()[0]
    return parent


def create_review_data(ui, repo, c, parent, rparent):
    'Returns a tuple of the diff and parent diff for the review.'
    diff = getdiff(ui, repo, c, parent)
    ui.debug('\n=== Diff from parent to rev ===\n')
    ui.debug(diff + '\n')

    if rparent != None and parent != rparent:
        parentdiff = getdiff(ui, repo, parent, rparent)
        ui.debug('\n=== Diff from rparent to parent ===\n')
        ui.debug(parentdiff + '\n')
    else:
        parentdiff = ''
    return diff, parentdiff
    
    
def send_review(ui, repo, c, parentc, diff, parentdiff, opts):
    reviewboard = getreviewboard(ui, opts)
    fields = createfields(ui, repo, c, parentc, opts)

    request_id = opts['existing']
    if request_id:
        update_review(request_id, ui, reviewboard, fields, diff, parentdiff, opts)
    else:
        request_id = new_review(ui, reviewboard, fields, diff, parentdiff, opts)

    request_url = '%s/%s/%s/' % (find_server(ui, opts), "r", request_id)

    if not request_url.startswith('http'):
        request_url = 'http://%s' % request_url

    msg = '\nreview request draft saved: %s\n'
    if opts['publish']:
        msg = '\nreview request published: %s\n'
    ui.status(msg % request_url)
    
    if ui.configbool('reviewboard', 'launch_webbrowser'):
        launch_webbrowser(ui, request_url)


def launch_webbrowser(ui, request_url):
    # not all python installations have this module, so only import it
    # when it's used
    from mercurial import demandimport
    demandimport.disable()
    import webbrowser
    demandimport.enable()
    
    ui.status('browser launched\n')
    webbrowser.open(request_url)


def getdiff(ui, repo, r, parent):
    '''return diff for the specified revision'''
    output = ""
    for chunk in patch.diff(repo, parent.node(), r.node()):
        output += chunk
    return output


def getreviewboard(ui, opts):
    '''We are going to fetch the setting string from hg prefs, there we can set
    our own proxy, or specify 'none' to pass an empty dictionary to urllib2
    which overides the default autodetection when we want to force no proxy'''
    http_proxy = ui.config('reviewboard', 'http_proxy' )
    if http_proxy:
        if http_proxy == 'none':
            proxy = {}
        else:
            proxy = { 'http':http_proxy }
    else:
        proxy=None
    
    server = find_server(ui, opts)
    
    ui.status('reviewboard: %s\n' % server)
    username = opts.get('username') or ui.config('reviewboard', 'user')
    if username:
        ui.status('username: %s\n' % username)
    password = opts.get('password') or ui.config('reviewboard', 'password')
    if password:
        ui.status('password: %s\n' % '**********')
    apiver = opts.get('apiver') or ui.config('reviewboard', 'apiver')
    if apiver:
        ui.status('apiver: %s\n' % apiver)

    try:
        return make_rbclient(server, username, password, proxy=proxy, apiver=apiver)
    except ReviewBoardError, msg:
        raise util.Abort(_(unicode(msg)))


def update_review(request_id, ui, reviewboard, fields, diff, parentdiff, opts):
    try:
        reviewboard.update_request(request_id, fields, diff, parentdiff)
        if opts['publish']:
            reviewboard.publish(request_id)
    except ReviewBoardError, msg:
        raise util.Abort(_(unicode(msg)))


def new_review(ui, reviewboard, fields, diff, parentdiff, opts):
    repo_id = find_reviewboard_repo_id(ui, reviewboard, opts)
    try:
        request_id = reviewboard.new_request(repo_id, fields, diff, parentdiff)
        if opts['publish']:
            reviewboard.publish(request_id)
    except ReviewBoardError, msg:
        raise util.Abort(_(unicode(msg)))

    return request_id


def find_reviewboard_repo_id(ui, reviewboard, opts):
    if opts.get('repoid'):
        return opts.get('repoid')
    elif ui.config('reviewboard','repoid'):
        return ui.config('reviewboard','repoid')

    try:
        repositories = reviewboard.repositories()
    except ReviewBoardError, msg:
        raise util.Abort(_(unicode(msg)))

    if not repositories:
        raise util.Abort(_('no repositories configured at %s' % server))

    repositories = sorted(repositories, key=operator.attrgetter('name'),
                          cmp=lambda x, y: cmp(x.lower(), y.lower()))
    
    remotepath = expandpath(ui, opts['outgoingrepo']).lower()
    repo_id = None
    for r in repositories:
        if r.tool != 'Mercurial':
            continue
        if r.path.lower() == remotepath:
            repo_id = str(r.id)
            ui.status('Using repository: %s\n' % r.name)
    if repo_id == None:
        ui.status('Repositories:\n')
        repo_ids = set()
        for r in repositories:
            if r.tool != 'Mercurial':
                continue
            ui.status('[%s] %s\n' % (r.id, r.name) )
            repo_ids.add(str(r.id))
        if len(repositories) > 1:
            repo_id = ui.prompt('repository id:', 0)
            if not repo_id in repo_ids:
                raise util.Abort(_('invalid repository ID: %s') % repo_id)
        else:
            repo_id = str(repositories[0].id)
            ui.status('repository id: %s\n' % repo_id)
    return repo_id


def createfields(ui, repo, c, parentc, opts):
    fields = {}
    
    all_contexts = find_contexts(repo, parentc, c, opts)

    changesets_string = 'changesets:\n'
    changesets_string += \
        ''.join(['%s:%s "%s"\n------------------------------\n' % (ctx.rev(), ctx, ctx.description()) \
                 for ctx in all_contexts])
    if opts['branch']:
        branch_msg = "review of branch: %s\n\n" % (c.branch())
        changesets_string = branch_msg + changesets_string
    ui.status(changesets_string + '\n')

    interactive = opts['interactive']
    request_id = opts['existing']
    # Don't clobber the summary and description for an existing request
    # unless specifically asked for    
    if opts['update'] or not request_id:
        
        # summary
        if opts["summary"]:
            default_summary = opts["summary"]
        else:
            default_summary = c.description().splitlines()[0]
        
        if interactive:
            ui.status('default summary: %s\n' % default_summary)
            ui.status('enter summary (or return for default):\n') 
            summary = readline().strip()
            if summary:
                fields['summary'] = summary
            else:
                fields['summary'] = default_summary
        else:
            fields['summary'] = default_summary

        # description
        if interactive:
            ui.status('enter description:\n')
            description = readline().strip()
            ui.status('append changesets to description? (Y/n):\n')
            choice = readline().strip()
            if choice != 'n':
                if description:
                    description += '\n\n'
                description += changesets_string
        else:
            description = changesets_string
        fields['description'] = description 
        
        fields['branch'] = c.branch()

    for field in ('target_groups', 'target_people', 'bugs_closed'):
        if opts.get(field):
            value = opts.get(field)
        else:
            value = ui.config('reviewboard', field)
        if value:
            fields[field] = value 
    
    return fields


def remoteparent(ui, repo, ctx, upstream=None):
    remotepath = expandpath(ui, upstream)
    if hasattr(localrepo, 'localpeer'):
        # hg >= 2.3
        remoterepo = hg.peer(repo, {}, remotepath)
        other = remoterepo.local()
        if other is not None:
            remoterepo = other
    else:
        # hg < 2.3
        remoterepo = hg.repository(ui, remotepath)
    
    out = findoutgoing(repo, remoterepo)
    
    for o in out:
        orev = repo[o]
        a, b, c = repo.changelog.nodesbetween([orev.node()], [ctx.node()])
        if a:
            return orev.parents()[0]


def findoutgoing(repo, remoterepo):
    # The method for doing this has changed a few times...
    try:
        from mercurial import discovery
    except ImportError:
        # Must be earlier than 1.6
        return repo.findoutgoing(remoterepo)

    try:
        version = float('.'.join(util.version().split('.')[:2]))
        if version >= 2.1:
            outgoing = discovery.findcommonoutgoing(repo, remoterepo)
            return outgoing.missing
        common, outheads = discovery.findcommonoutgoing(repo, remoterepo)
        return repo.changelog.findmissing(common=common, heads=outheads)
    except AttributeError:
        # Must be earlier than 1.9
        return discovery.findoutgoing(repo, remoterepo)


def expandpath(ui, upstream):
    if upstream:
        return ui.expandpath(upstream)
    else:
        return ui.expandpath(ui.expandpath('reviewboard', 'default-push'),
            'default')


def check_parent_options(opts):
    usep = bool(opts['parent'])
    useg = bool(opts['outgoingchanges'])
    useb = bool(opts['branch'])
    
    if (usep or useg or useb) and not (usep ^ useg ^ useb):
        raise util.Abort(_(
           "you cannot combine the --parent, --outgoingchanges "
           "and --branch options"))
           
    if useg and not (opts.get('outgoing') or opts.get('outgoingrepo')):
        msg = ("When using the -g/--outgoingchanges flag, you must also use "
            "either the -o or the -O <repo> flag.")
        raise util.Abort(msg)


def find_branch_parent(ui, ctx):
    '''Find the parent revision of the 'ctx' branch.'''
    branchname = ctx.branch()
    
    getparent = lambda ctx: ctx.parents()[0]
    
    currctx = ctx
    while getparent(currctx) and currctx.branch() == branchname:
        currctx = getparent(currctx)
        ui.debug('currctx rev: %s; branch: %s\n' % (currctx.rev(), 
                                            currctx.branch()))
                                            
    # return the root of the repository if the first
    # revision is on the branch
    if not getparent(currctx) and currctx.branch() == branchname:
        return currctx._repo['000000000000']
    
    return currctx


def find_contexts(repo, parentctx, ctx, opts):
    """Find all context between the contexts, excluding the parent context."""
    contexts = []
    for node in repo.changelog.nodesbetween([parentctx.node()],[ctx.node()])[0]:
        currctx = repo[node]
        if node == parentctx.node():
            continue
        # only show nodes on the current branch
        if opts['branch'] and currctx.branch() != ctx.branch():
            continue
        contexts.append(currctx)
    contexts.reverse()
    return contexts


def find_server(ui, opts):
    server = opts.get('server')
    if not server:
        server = ui.config('reviewboard', 'server')
    if not server:
        msg = 'please specify a reviewboard server in your .hgrc file or using the --server flag'
        raise util.Abort(_(unicode(msg)))
    return server


def readline():
    line = sys.stdin.readline()
    return line


cmdtable = {
    "postreview":
        (postreview,
        [
        ('o', 'outgoing', False,
         _('use upstream repository to determine the parent diff base')),
        ('O', 'outgoingrepo', '',
         _('use specified repository to determine the parent diff base')),
        ('i', 'repoid', '',
         _('specify repository id on reviewboard server')),
        ('s', 'summary', '', _('specify a summary for the review request')),
        ('m', 'master', '',
         _('use specified revision as the parent diff base')),
        ('', 'server', '', _('ReviewBoard server URL')),
        ('e', 'existing', '', _('existing request ID to update')),
        ('u', 'update', False, _('update the fields of an existing request')),
        ('p', 'publish', None, _('publish request immediately')),
        ('', 'parent', '', _('parent revision for the uploaded diff')),
        ('g', 'outgoingchanges', False, 
            _('create diff with all outgoing changes')),
        ('b', 'branch', False, 
            _('create diff of all revisions on the branch')),
        ('I', 'interactive', False, 
            _('override the default summary and description')),
        ('U', 'target_people', '', 
            _('comma separated list of people needed to review the code')),
        ('G', 'target_groups', '', 
            _('comma separated list of groups needed to review the code')),
        ('B', 'bugs_closed', '', 
            _('comma separated list of bug IDs addressed by the change')),
        ('', 'username', '', _('username for the ReviewBoard site')),
        ('', 'password', '', _('password for the ReviewBoard site')),
        ('', 'apiver', '', _('ReviewBoard API version (e.g. 1.0, 2.0)')),
        ],
        _('hg postreview [OPTION]... [REVISION]')),
}
