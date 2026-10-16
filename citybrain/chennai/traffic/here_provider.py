"""HERE Traffic API v7 flow + optional incidents; see CHENNAI_LIVE_TRAFFIC.md."""
from .provider import HTTPProvider, FetchResult, bounds
from .normalization import here_rows


class HERETrafficProvider(HTTPProvider):
    name, env_key = 'HERE', 'HERE_API_KEY'

    def __init__(self, *, study_bounds=(80.132,12.823,80.174,12.863), incidents=False, **kwargs):
        super().__init__(**kwargs)
        self.bounds, self.incidents = bounds(study_bounds), incidents

    def request(self, now):
        params = {'in':'bbox:'+','.join(map(str,self.bounds)), 'locationReferencing':'shape','apiKey':self._key}
        rows, errors = here_rows(self.transport('https://data.traffic.hereapi.com/v7/flow',params,self.timeout),now)
        if self.incidents:
            # A separate explicitly enabled transaction; same bounded study area.
            extra, invalid = here_rows(self.transport('https://data.traffic.hereapi.com/v7/incidents',params,self.timeout),now,incidents=True)
            rows.extend(extra); errors.extend(invalid)
        return FetchResult(rows,'FETCHED' if rows else 'COVERAGE_UNVERIFIED_OR_INSUFFICIENT',errors)
