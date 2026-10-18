# Optional traffic-provider evaluation

Public documentation checked 19 October 2026; **no traffic data API requests were made**. This is a technical/licensing evaluation, not measured Chennai coverage or accuracy evidence. Prices/terms depend on account, region, SKU and current contract; obtain an approved quote and hard quotas before enabling anything.

| Option | Existing reuse / technical fit | Coverage and accuracy evidence here | Cost/licensing gate |
|---|---|---|---|
| HERE Traffic v7 | Existing bounded-bbox flow and optional separate incident adapter, SI normalization and directed shape matching. Best initial code-reuse candidate for the pilot. | Mocked tests and synthetic replay only. Genuine Chennai responses, completeness, road precision and source-time behavior unverified. | Account/plan, permitted display/storage, attribution, rate/quota and incident-request charging must be checked against the actual agreement. |
| TomTom Flow Segment | Existing single configured-point request; returned segment flow is not citywide coverage. Reuse adapter/error/normalization contracts. Unknown time or direction remains ineligible. | No genuine response observed. Standard response fields cannot be assumed to prove source timestamp/direction. | Account-specific pricing, permitted caching/display and attribution require verification. No free-tier assumption authorizes a request. |
| Google Routes | Optional managed route computation rather than direct edge-flow replacement. TRAFFIC_AWARE and TRAFFIC_AWARE_OPTIMAL are distinct preferences. No adapter implemented. | Google describes OPTIMAL as a more exhaustive traffic-aware search with higher latency; that is provider documentation, not project-measured Chennai/ambulance accuracy. | Billing and quotas required; traffic-aware options use advanced/Pro features. Standard map-display policy requires a Google Map for mapped Routes results. Do not render Google routes on Cesium/OSM under an assumed license. |

Google's policy restricts caching most Routes content; the place-ID exception does not authorize retaining arbitrary route geometry/traffic data. Applications need compliant public terms/privacy policy and attribution. A compatible future option is a **separate Google Maps-rendered view** after license/account review, with Google content kept out of the Cesium/OSM path. No request, SDK or mandatory dependency was added.

Recommendation: retain the offline-first provider abstraction and initially investigate HERE under an expressly approved bounded pilot because its area/geometry interface aligns with the existing code. This is an engineering fit judgment, **not a claim HERE is more accurate or cheaper**. Compare authorized genuine samples and licenses before selecting a provider. TomTom may be suitable when genuine direction/time evidence exists; one-point coverage cannot support Chennai-wide claims. Google needs separate rendering/licensing design and approved budget.

Primary references:

- [HERE flow request](https://docs.here.com/traffic-api/docs/how-to-request-flow-data), [HERE API setup / pricing entry](https://docs.here.com/traffic-api/docs/send-request-readme).
- [TomTom Flow Segment documentation](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data).
- [Google traffic preferences](https://developers.google.com/maps/documentation/routes/config_trade_offs).
- [Google usage/billing and quotas](https://developers.google.com/maps/documentation/routes/usage-and-billing).
- [Google Routes display/caching/attribution policies](https://developers.google.com/maps/documentation/routes/policies).

These documentation pages are not permission to activate APIs. HERE/TomTom non-Google-map rights are unresolved for the specific account; no blanket permission is claimed. Actual fees, quotas and legally permitted retention remain required authorizations.
