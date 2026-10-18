# CityBrain V3.1 technical viva questions

1. **What is CityBrain?** A modular emergency-response coordination software
   prototype combining a SUMO Chennai digital twin, state-aware planning,
   verified simulated route execution, isolated traffic observation and a
   visualization dashboard.
2. **Which geography is used?** OSM-derived roads for a bounded Chennai study
   area; the network and routing are simulated in SUMO.
3. **What is real and what is simulated?** Road geometry is sourced from OSM;
   vehicles, demand, incidents, signals, capacity and response outcomes are
   simulated.
4. **What does SUCCESS mean?** The simulated ambulance reached its configured
   hospital access road; it does not prove clinical arrival or admission.
5. **How is a route accepted?** The existing planner proposes; validation checks
   the route; `RouteExecutor` applies it; physical route read-back must succeed
   before logical acceptance.
6. **Does the traffic sidecar alter Core state?** No. It computes separate
   bounded candidate costs and evidence; canonical measurements remain intact.
7. **How is the experimental advisor enabled?** Only with
   `--experimental-traffic-evaluation`; the normal launcher leaves it off.
8. **Can that advisor re-route an ambulance?** No. It displays
   `ADVISORY_RECOMMENDATION`, KEEP or NO_ROUTE and never calls the planner or
   executor.
9. **What traffic checks gate it?** Provenance, source/retrieval time, freshness,
   known direction, verified directed road match, confidence, coverage, speed,
   and conflict checks.
10. **How does it avoid weak alternatives?** It requires directed connectivity,
    minimum absolute and proportional improvement, route commitment, cooldown,
    and no recent-route oscillation.
11. **What does a missing timestamp mean?** Freshness stays UNKNOWN and the
    observation cannot affect the experimental cost.
12. **What happens to a future timestamp?** TrafficService quarantines it before
    updating the current stream, preserving the last valid observation.
13. **What is the meaning of replay traffic?** A stored synthetic/offline sample
    that tests data flow; it is not a provider response or live measurement.
14. **Were HERE or TomTom called for this work?** No. The adapters are
    implemented but not live-verified; coverage, accuracy, account costs and
    returned Chennai geometry are unknown.
15. **Are API credentials stored in the repository?** No. The sample
    configuration uses empty values, and readiness checks do not send requests.
16. **Can external observations trigger replanning?** No. They are isolated from
    the planner and are display-only under the opt-in feature.
17. **What does the 20-second stability guard do?** It confirms soft route-change
    proposals over time while leaving genuine hard invalidations to existing
    handling.
18. **Are all replans delayed by the guard?** No. Physical invalidation or
    explicit blockage is handled through the hard-failure path.
19. **Does CityBrain control municipal signals?** No.
20. **Why is SUMO signal priority disabled?** The two imported programs do not
    provide a reviewed movement mapping, minimum-green contract, guaranteed
    clearance phases and restoration policy. A junction recommendation alone
    cannot verify the requested movement.
21. **What signal evidence does the system display?** SUMO phase, controlled-link
    state and phase timing when TraCI provides it consistently.
22. **Does the GPS feature track other cars?** No. It is a browser user's own
    location after explicit permission.
23. **Where does browser location live?** In the active browser tab's memory. It
    is not uploaded, written to result files or sent to providers.
24. **Why is there no local GPS runtime endpoint?** The tab-local marker serves
    visualization without introducing coordinate transport or a new lifecycle;
    no accepted planner behavior needs it.
25. **What happens if the Cesium viewer fails?** The dashboard retains an SVG
    fallback; dashboard failures are isolated from SUMO and CityBrain runtime.
26. **What does the ten-seed study compare?** Existing static and dynamic
    strategies on S05/S06/S08 using matched seeds and the same normal synthetic
    demand.
27. **Did the study evaluate the traffic advisor?** No. The legacy trial runner
    does not execute advisor recommendations, so it was not counted as an arm.
28. **How are failures treated?** SUCCESS, TELEPORTED, NO_ROUTE, TIMEOUT, ERROR
    and other statuses stay in each arm's completion denominator.
29. **What are the study's limits?** Ten seeds per scenario and one normal-demand
    profile give broad uncertainty and do not establish general superiority or
    real-world performance.
30. **What did S06 show?** Both static and dynamic arms teleported in all ten
    runs, identifying a failure boundary for this configured scenario.
31. **What is a paired travel-time result?** A static-minus-dynamic response-time
    difference for the same seed only when both arms succeeded; failed pairs
    receive no fabricated travel time.
32. **Were historical trials regenerated?** No. New experiments use a separate
    versioned output path; the frozen 2,172-entry manifest still validates.
33. **What was the experiment runner defect?** S08 rows include extra fields and
    CSV serialization assumed the first row schema. The writer now exports the
    union of row columns; prior per-trial checkpoints were resumed, not erased.
34. **What evidence supports browser claims?** Chrome browser automation checked
    replay vehicle/route rendering, signal state, traffic overlays, labels,
    closure lifecycle, future-clock recovery, advisor disclosure and fallback.
    Provider behavior was mocked/replay only.
35. **Is the system production-ready for emergency response?** No. Live data,
    calibrated traffic, actual signal control, hospital services, field
    validation and safety certification are absent.
