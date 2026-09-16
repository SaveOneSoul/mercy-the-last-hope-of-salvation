"""CI-only urllib hook for authenticated GitHub API reads.

GitHub-hosted runners share a low unauthenticated API rate limit. Logos source
importers verify immutable Git tree identities through api.github.com, so CI
adds the ephemeral workflow token only to those API requests. Raw source blobs
remain fetched from their immutable raw.githubusercontent.com commit URLs and
are still verified by Git blob SHA-1 / SHA-256 in the importers.
"""

from __future__ import annotations

import os
import urllib.request

_ORIGINAL_REQUEST = urllib.request.Request
_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def _authenticated_request(url, *args, **kwargs):
    headers = dict(kwargs.pop("headers", {}) or {})
    target = str(url)
    if _TOKEN and target.startswith("https://api.github.com/"):
        headers.setdefault("Authorization", f"Bearer {_TOKEN}")
        headers.setdefault("X-GitHub-Api-Version", "2022-11-28")
        headers.setdefault("Accept", "application/vnd.github+json")
    return _ORIGINAL_REQUEST(url, *args, headers=headers, **kwargs)


urllib.request.Request = _authenticated_request
