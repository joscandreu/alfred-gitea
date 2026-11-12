# encoding: utf-8
"""Background job: fetch all repositories from Gitea into the cache."""
import mureq
from workflow import Workflow

import gitea_common as gc

log = None

PAGE_LIMIT = 50          # Gitea's default MAX_RESPONSE_ITEMS
MAX_PAGES = 1000         # safety net against a misbehaving server
READ_LIMIT = 20 * 1024 * 1024  # max bytes per response


def get_projects(api_key, url, ssl_context):
    """Fetch all pages of projects.

    :return: list
    """
    projects = []
    headers = gc.api_headers(api_key)
    for page in range(1, MAX_PAGES + 1):
        log.info('Calling API page %d', page)
        params = dict(limit=PAGE_LIMIT, page=page)
        r = mureq.get(url, params=params, headers=headers,
                      ssl_context=ssl_context, read_limit=READ_LIMIT)
        r.raise_for_status()

        data = r.json().get('data') or []
        projects.extend(data)

        total = r.headers.get('x-total-count')
        log.debug('page %d: %d repos, %d so far, total %s', page, len(data), len(projects), total)
        if not data or (total is not None and len(projects) >= int(total)):
            break
    return projects


def main(wf):
    wf.cache_serializer = gc.CACHE_SERIALIZER
    try:
        api_key = gc.get_secret(wf, gc.API_KEY_ACCOUNT)
        base_url = gc.get_base_url(wf)
        if not api_key or not base_url:
            log.error('Access token or URL not configured')
            return
        api_url = base_url + gc.API_SEARCH_PATH
        ssl_context = gc.build_ssl_context(wf, log)

        def wrapper():
            return get_projects(api_key, api_url, ssl_context)

        projects_gitea = wf.cached_data(gc.CACHE_KEY, wrapper, max_age=gc.CACHE_MAX_AGE)
        wf.cache_data(gc.ERROR_CACHE_KEY, None)  # clear previous error
        log.info('%d gitea repos cached', len(projects_gitea))

    except gc.ConfigError as e:
        log.error('Configuration error: %s', e)
        wf.cache_data(gc.ERROR_CACHE_KEY, str(e))
    except mureq.HTTPErrorStatus as e:
        msg = 'HTTP {} from Gitea'.format(e.status_code)
        if e.status_code in (401, 403):
            msg += ' - check your access token (`tea set token`)'
        log.error(msg)
        wf.cache_data(gc.ERROR_CACHE_KEY, msg)
    except Exception as e:  # network/TLS errors etc.
        log.exception('Update failed')
        wf.cache_data(gc.ERROR_CACHE_KEY, '{}: {}'.format(type(e).__name__, e))


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    wf.run(main)
