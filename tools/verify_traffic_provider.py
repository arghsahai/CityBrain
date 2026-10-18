#!/usr/bin/env python3
"""Report provider readiness; a live request requires an explicit command flag."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citybrain.chennai.traffic.verification import verification_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=('here','tomtom'), required=True)
    parser.add_argument('--authorize-live-request', action='store_true',
        help='Make one potentially billable authenticated provider request. Use only after reviewing account terms and obtaining authorization.')
    args = parser.parse_args()
    provider_name = 'HERE' if args.provider == 'here' else 'TOMTOM'
    configured = bool(os.environ.get(provider_name+'_API_KEY'))
    if not args.authorize_live_request:
        report = verification_report(provider_name, configured=configured)
    elif not configured:
        report = verification_report(provider_name, configured=False)
    else:
        # Never print the key, URL, payload, or provider exception text.
        from citybrain.chennai.traffic import HERETrafficProvider, TomTomTrafficProvider
        cls = HERETrafficProvider if provider_name == 'HERE' else TomTomTrafficProvider
        result = cls(authorized=True).fetch(datetime.now(timezone.utc))
        report = verification_report(provider_name, configured=True, requested=True,
                                     fetch_result=result, now=datetime.now(timezone.utc))
    print(json.dumps(report, indent=2))
    if report['status'] in {'NOT_CONFIGURED','CONFIGURED_NOT_VERIFIED'}:
        return 2
    return 0 if report['status'] == 'VERIFIED' else 1


if __name__ == '__main__':
    sys.exit(main())
