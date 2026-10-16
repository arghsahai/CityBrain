"""Bounded HTTP boundary. Credentials alone never authorize paid requests."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import os
import socket
from typing import Protocol
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


@dataclass
class FetchResult:
    observations: list = field(default_factory=list)
    status: str = 'UNAVAILABLE'
    errors: list = field(default_factory=list)
    retry_after: float = 0


class TrafficProvider(Protocol):
    name: str
    def fetch(self, now: datetime) -> FetchResult: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward query credentials to a redirect target.


def http_json(endpoint, params, timeout):
    request = Request(endpoint+'?'+urlencode(params), headers={'Accept':'application/json'})
    with build_opener(NoRedirect).open(request, timeout=timeout) as response:
        payload = response.read(2*1024*1024+1)
        if len(payload) > 2*1024*1024:
            raise ValueError('Response exceeds 2 MiB limit')
        return json.loads(payload)


def retry_delay(value, now):
    try:
        result = float(value)
    except (ValueError, TypeError):
        try:
            result = (parsedate_to_datetime(value)-now).total_seconds()
        except (ValueError, TypeError, OverflowError):
            result = 60
    return max(1, result) if math.isfinite(result) else 60


class HTTPProvider:
    name = ''
    env_key = ''

    def __init__(self, *, api_key=None, authorized=False, timeout=5, transport=None):
        if isinstance(timeout,bool) or not math.isfinite(timeout) or not 0 < timeout <= 30:
            raise ValueError('Timeout must be within (0,30] seconds')
        self._key = os.environ.get(self.env_key) if api_key is None else api_key
        self.authorized, self.timeout = authorized, timeout
        self.transport = transport or http_json

    @property
    def status(self):
        return 'NOT_CONFIGURED' if not self._key else 'READY_BUT_NOT_TESTED' if not self.authorized else 'READY'

    def fetch(self, now):
        if self.status != 'READY':
            return FetchResult(status=self.status)
        try:
            return self.request(now)
        except HTTPError as error:
            status = ('AUTHENTICATION_ERROR' if error.code in (401,403) else
                      'RATE_LIMITED' if error.code == 429 else 'PROVIDER_UNAVAILABLE')
            # Never propagate provider text, exception URLs or credential values.
            return FetchResult(status=status, errors=[status], retry_after=retry_delay(error.headers.get('Retry-After'),now) if error.code in (429,503) else 60)
        except (TimeoutError, socket.timeout):
            return FetchResult(status='TIMEOUT',errors=['TIMEOUT'],retry_after=60)
        except (URLError, OSError):
            return FetchResult(status='PROVIDER_UNAVAILABLE',errors=['PROVIDER_UNAVAILABLE'],retry_after=60)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            return FetchResult(status='INVALID_RESPONSE',errors=['INVALID_RESPONSE'],retry_after=60)

    def observations(self, now):
        """Compatibility for old callers; the launcher uses the background service."""
        result = self.fetch(now)
        return dict(provider=self.name, source='UNAVAILABLE', status=result.status,
                    observations=[o.to_dict() for o in result.observations], errors=result.errors)


def bounds(value):
    if len(value) != 4 or any(isinstance(v,bool) or not math.isfinite(v) for v in value):
        raise ValueError('Invalid study bounds')
    w,s,e,n = value
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90) or e-w > .1 or n-s > .1:
        raise ValueError('Bounds must be a small study area (<=0.1 degree per side)')
    return tuple(value)
