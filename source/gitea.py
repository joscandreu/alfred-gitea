# encoding: utf-8
import sys
import argparse
from workflow import Workflow3, ICON_ERROR, ICON_WARNING, ICON_INFO
from workflow.background import run_in_background, is_running

import gitea_common as gc

log = None


def search_for_project(project):
    """Generate a string search key for a project"""
    return u' '.join([project.get('full_name') or '', project.get('description') or ''])


def set_secret(wf, account, value, prompt, label):
    """Store a secret from the CLI argument or, if empty, a hidden dialog.

    Prints a status message, which Alfred shows as notification text.
    """
    if not value:
        value = gc.prompt_hidden(prompt)
    if value is None:
        print('Cancelled, {} not changed.'.format(label))
        return 0
    value = value.strip()
    if not value:
        gc.delete_secret(wf, account)
        print('{} removed.'.format(label))
        return 0
    gc.save_secret(wf, account, value)
    log.info('Saved %s', label)
    print('{} saved to Keychain.'.format(label))
    return 0


def main(wf):
    parser = argparse.ArgumentParser()
    # `nargs='?', const=''` so that `--setkey` without value opens a dialog
    parser.add_argument('--setkey', dest='apikey', nargs='?', const='', default=None)
    parser.add_argument('--setcertpass', dest='certpass', nargs='?', const='', default=None)
    parser.add_argument('--seturl', dest='apiurl', nargs='?', const='', default=None)
    parser.add_argument('query', nargs='?', default=None)
    args = parser.parse_args(wf.args)

    ####################################################################
    # Settings actions (called from "Run Script" actions)
    ####################################################################

    if args.apikey is not None:
        return set_secret(wf, gc.API_KEY_ACCOUNT, args.apikey,
                          'Gitea access token:', 'Access token')

    if args.certpass is not None:
        return set_secret(wf, gc.CERT_PASS_ACCOUNT, args.certpass,
                          'Passphrase of the client certificate private key '
                          '(leave empty to remove):', 'Client key passphrase')

    if args.apiurl is not None:
        try:
            base_url = gc.normalize_base_url(args.apiurl)
        except gc.ConfigError as e:
            print('Invalid URL: {}'.format(e))
            return 0
        if wf.settings.get('base_url') != base_url:
            wf.settings['base_url'] = base_url
            wf.settings['api_url'] = base_url + gc.API_SEARCH_PATH
            # Never show repos from a previous instance
            wf.clear_cache()
        log.info('Gitea URL set to %s', base_url)
        print('Gitea URL set to {}'.format(base_url))
        return 0

    ####################################################################
    # Check configuration
    ####################################################################

    if not gc.get_secret(wf, gc.API_KEY_ACCOUNT):
        wf.add_item('No API key set',
                    'Please use `tea set token` to set your Gitea access token.',
                    valid=False,
                    icon=ICON_ERROR)
        wf.send_feedback()
        return 0

    base_url = gc.get_base_url(wf)
    if not base_url:
        wf.add_item('No Gitea URL set',
                    'Please use `tea set url https://<host>` to set your Gitea URL.',
                    valid=False,
                    icon=ICON_ERROR)
        wf.send_feedback()
        return 0

    ####################################################################
    # View/filter gitea Projects
    ####################################################################

    query = args.query

    projects_gitea = wf.cached_data(gc.CACHE_KEY, None, max_age=0)
    update_error = wf.cached_data(gc.ERROR_CACHE_KEY, None, max_age=0)

    if update_error:
        wf.add_item('Error updating project list',
                    update_error,
                    valid=False,
                    icon=ICON_ERROR)

    # Notify the user if the cache is being updated
    if is_running('update') and not projects_gitea:
        log.info("Updating project list via gitea..")
        wf.rerun = 0.5
        wf.add_item('Updating project list via gitea...',
                    subtitle=u'This can take some time if you have a large number of projects.',
                    valid=False,
                    icon=ICON_INFO)

    # Start update script if cached data is too old (or doesn't exist)
    if not wf.cached_data_fresh(gc.CACHE_KEY, max_age=gc.CACHE_MAX_AGE) and not is_running('update'):
        cmd = ['/usr/bin/python3', wf.workflowfile('update.py')]
        run_in_background('update', cmd)
        wf.rerun = 0.5

    # Only offer repos whose URL points to the configured instance
    projects_gitea = [p for p in (projects_gitea or [])
                      if gc.is_url_on_instance(p.get('html_url'), base_url)]

    # If script was passed a query, use it to filter projects
    if query and projects_gitea:
        projects_gitea = wf.filter(
            query, projects_gitea, key=search_for_project, min_score=20)

    if not projects_gitea:  # we have no data to show, so show a warning and stop
        if not update_error:
            wf.add_item('No projects found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    for project in projects_gitea:
        wf.add_item(title=project['full_name'],
                    subtitle=project.get('description') or '',
                    arg=project['html_url'],
                    valid=True,
                    icon=wf.workflowfile('gitea-transparent.png'),
                    largetext=project['full_name'],
                    quicklookurl=project['html_url'],
                    copytext=project['html_url'],
                    uid=str(project['id']))

    wf.send_feedback()
    return 0


if __name__ == u"__main__":
    # Self-updating from GitHub is intentionally disabled: it would download
    # and install unsigned code from the (archived) upstream repository and
    # overwrite this customised version.
    wf = Workflow3()
    wf.cache_serializer = gc.CACHE_SERIALIZER
    log = wf.logger
    sys.exit(wf.run(main))
