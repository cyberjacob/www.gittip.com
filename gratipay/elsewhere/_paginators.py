"""Helper functions to handle pagination of API responses
"""
from __future__ import unicode_literals

from urllib import urlencode
from urlparse import parse_qs, urlsplit, urlunsplit


def _modify_query(url, key, value):
    scheme, netloc, path, query, fragment = urlsplit(url)
    query = parse_qs(query)
    if value is None:
        query.pop(key, None)
    else:
        query[key] = [value]
    query = urlencode(query, doseq=True)
    return urlunsplit((scheme, netloc, path, query, fragment))


def _strip_prefix(prefix, s):
    """
    >>> str(_strip_prefix('https://api.example.com', 'https://api.example.com/foo/bar'))
    '/foo/bar'
    >>> _strip_prefix('https://api.example.org', 'https://api.example.com/baz')
    Traceback (most recent call last):
        ...
    ValueError: "https://api.example.org" is not a prefix of "https://api.example.com/baz"
    """
    i = len(prefix)
    if s[:i] == prefix:
        return s[i:]
    raise ValueError('"%s" is not a prefix of "%s"' % (prefix, s))


links_keys = set('prev next first last'.split())


def cursor_paginator():
    # https://dev.twitter.com/overview/api/cursoring
    links_keys_map = (('prev', 'previous_cursor'), ('next', 'next_cursor'))
    def f(self, response, parsed):
        url = _strip_prefix(self.api_url, response.request.url)
        links = {k: _modify_query(url, param, parsed[k2])
                 for k, k2 in links_keys_map
                 if parsed.get(k2)}
        if links.get('prev') and not links.get('first'):
            links['first'] = _modify_query(url, param, None)
        lists = [a for a in parsed.values() if isinstance(a, list)]
        assert len(lists) == 1
        page = next(iter(lists))
        total_count = -1 if links else len(page)
        return page, total_count, links
    return f


def header_links_paginator():
    # https://developer.github.com/v3/#pagination
    def f(self, response, parsed):
        links = {k: _strip_prefix(self.api_url, v['url'])
                 for k, v in response.links.items()
                 if k in links_keys}
        total_count = -1 if links else len(parsed)
        return parsed, total_count, links
    return f


def keys_paginator(**kw):
    # https://confluence.atlassian.com/display/BITBUCKET/Version+2#Version2-Pagingthroughobjectcollections
    page_key = kw.get('page', 'values')
    total_count_key = kw.get('total_count', 'size')
    links_keys_map = tuple((k, kw.get(k, k)) for k in links_keys)
    def f(self, response, parsed):
        page = parsed[page_key]
        links = {k: _strip_prefix(self.api_url, parsed[k2])
                 for k, k2 in links_keys_map
                 if parsed.get(k2)}
        total_count = parsed.get(total_count_key, -1) if links else len(page)
        return page, total_count, links
    return f
