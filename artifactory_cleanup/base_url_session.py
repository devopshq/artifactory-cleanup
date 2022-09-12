from urllib.parse import urljoin

import requests


class BaseUrlSession(requests.Session):
    """
    Perform all queries based on the base URL

    If base url is "http://example.com/" then session.get("/api/version/") queries "http://example.com/api/version/"
    """

    def __init__(self, base_url=None):
        super(BaseUrlSession, self).__init__()
        self.base_url = base_url.rstrip("/") + "/"

    def request(self, method, url, *args, **kwargs):
        if not url.startswith("http://") or url.startswith("https://"):
            url = url.lstrip("/")
            url = urljoin(self.base_url, url)

        return super(BaseUrlSession, self).request(method, url, *args, **kwargs)
