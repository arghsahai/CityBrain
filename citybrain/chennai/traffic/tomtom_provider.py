"""One configured TomTom Flow Segment query per poll, never a city-wide crawl."""
from .provider import HTTPProvider, FetchResult, bounds
from .normalization import tomtom_row


class TomTomTrafficProvider(HTTPProvider):
    name, env_key = 'TOMTOM', 'TOMTOM_API_KEY'

    def __init__(self, *, point=(12.8408,80.154), study_bounds=(80.132,12.823,80.174,12.863), **kwargs):
        super().__init__(**kwargs)
        self.bounds = bounds(study_bounds)
        lat,lon = point
        w,s,e,n = self.bounds
        if not (s <= lat <= n and w <= lon <= e):
            raise ValueError('TomTom point outside study area')
        self.point = point

    def request(self, now):
        params = {'key':self._key,'point':','.join(map(str,self.point)),'unit':'kmph','openLr':'true'}
        data = self.transport('https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/16/json',params,self.timeout)
        return FetchResult([tomtom_row(data,now)],'FETCHED')
