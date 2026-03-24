# encoding: utf-8
from workflow import Workflow, Workflow3, ICON_WEB, ICON_WARNING, ICON_INFO, web, PasswordNotFound
# from workflow import web, Workflow3, PasswordNotFound
import mureq
from tls import build_ssl_context

# log = None


def get_projects(api_key, url, ssl_context=None):
    """
    Parse all pages of projects
    :return: list
    """
    return get_project_page(api_key, url, 1, [], ssl_context=ssl_context)


def get_project_page(api_key, url, page, list, ssl_context=None):
    log.info("Calling API page {page}".format(page=page))
    params = dict(token=api_key, per_page=100, page=page, membership='true')
    r = mureq.get(url, params=params, ssl_context=ssl_context)

    log.debug('URL: %s', url)

    # throw an error if request failed
    # Workflow will catch this and show it to the user
    r.raise_for_status()

    # Parse the JSON returned by Gitea and extract the projects
    # result = list + r.json()['data']
    projects_gitea = list + r.json()['data']

    log.debug(projects_gitea)

    # count the total amounts of items from the http header
    total_count = int(r.headers.get('x-total-count'))
    # because api call is made with per_page=100, we get roughly 2 repos per call
    pages_count = total_count // 2
    log.debug('pages count: %s', pages_count)

    page = page + 1
    log.debug('NEXTPAGE: %s', page)
    if page < pages_count + 1:
        log.debug('nextpage', page)
        projects_gitea = get_project_page(
            api_key, url, page, projects_gitea, ssl_context=ssl_context)

    return projects_gitea


def main(wf):
    try:
        # Get API key from Keychain
        api_key = wf.get_password('gitea_api_key')
        api_url = wf.settings.get('api_url')
        ssl_ctx = build_ssl_context(wf.settings, wf.get_password)

        # Retrieve projects from cache if available and no more than 600
        # seconds old
        def wrapper():
            return get_projects(api_key, api_url, ssl_context=ssl_ctx)

        projects_gitea = wf.cached_data(
            'projects_gitea', wrapper, max_age=3600)

        # Record our progress in the log file
        log.info('{} gitea repos cached'.format(len(projects_gitea)))

    except PasswordNotFound:  # API key has not yet been set
        # Nothing we can do about this, so just log it
        log.error('No API key saved')


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    wf.run(main)
