# Krishna's viva bank — 40 questions

Answers describe the frozen repository and official evidence, not proposed future work. Numerical sources are RESULT_TABLES.md and RESEARCH_PACKAGE.md; technical context is the repository's SUMO/TraCI implementation. For general teleport semantics, see the [official SUMO explanation](https://sumo.dlr.de/docs/Simulation/Why_Vehicles_are_teleporting.html).

## EASY

### 1. What was your primary contribution?

**Short answer:** I developed the regression SUMO environment, scenario/traffic tooling, paired experimental workflow and research validation. I also contributed final integration and exception-safety work, while crediting Argh's Core and Subhashini's planner foundations.

**Deeper answer:** The contribution map ties each tracked file to actual Git authorship. The initial team SUMO assets came from Argh, so I do not claim to have originated every file under simulation/. My research contribution includes outcome correctness, provenance, seeded trials, analysis and reproducible demonstrations.

### 2. What is SUMO doing here?

**Short answer:** SUMO models individual vehicles moving through a synthetic road network with traffic interactions and signals. It provides the physical simulation against which CityBrain routes are applied and measured.

**Deeper answer:** The planner does not animate cars itself. TraCI observations describe the simulated environment, and route commands change the ambulance's future path in that environment. This separation makes physical execution observable.

### 3. What is TraCI?

**Short answer:** TraCI is the interface used to exchange state and commands with the running traffic simulation. CityBrain reads vehicle/road measurements and applies routes through it.

**Deeper answer:** The final architecture centralizes route application in Core's executor. The dashboard does not open a TraCI connection; it observes persisted runtime evidence instead. Observation and actuation therefore remain separate responsibilities.

### 4. Why use the term digital twin?

**Short answer:** We use it in the bounded sense of a simulation-based traffic representation coupled to an observe–decide–apply–measure loop. It is not a live synchronized representation of Chennai or another city.

**Deeper answer:** SUMO supplies evolving state, CityBrain reasons over that state and physical simulation results feed later decisions. The absence of real sensor synchronization and calibration limits the claim. Calling it a live operational city twin would overstate the evidence.

### 5. What network did you evaluate?

**Short answer:** The main regression network has nine junctions and 24 directed external edges. S08 uses a separate extension with 12 junctions and 34 edges.

**Deeper answer:** The extension adds a northern row and an alternative approach to H1. Both networks are engineered synthetic grids with signal programs, not extracted real-city networks. Internal junction edges are excluded from the quoted external-edge counts.

### 6. Where is the hospital?

**Short answer:** H1 is configured at junction J9. It is destination metadata with static availability, not a simulated building or live hospital feed.

**Deeper answer:** The final runtime checks route endpoints against this configuration before execution. Successful arrival must agree with the accepted destination. This does not model hospital queues, patient triage or bed reservation changes.

### 7. How does the ambulance differ from a car?

**Short answer:** It has a distinct vehicle type, including configured maximum speed 20 m/s and different acceleration/deceleration parameters. It still obeys the simulated environment rather than receiving an implemented CityBrain green corridor.

**Deeper answer:** The experiment runner sets vClass to emergency, but does not enable a blue-light bypass mechanism. Configured maximum speed is not realized average speed. Route and signal constraints can still slow or block it.

### 8. What are normal, heavy and peak traffic?

**Short answer:** They multiply the four base traffic flows by 1, 1.5 and 2. Their total scheduled rates are 1,400, 2,100 and 2,800 vehicles per hour.

**Deeper answer:** These are demand inputs, not guaranteed completed arrivals. Insertion delays and traffic interactions affect realized traffic. S07's additional slow-car flow is separate and unscaled.

### 9. How are accidents modelled?

**Short answer:** The scenario inserts accidentVehicle objects with scheduled stops on selected roads. This creates controlled obstruction and changing traffic conditions.

**Deeper answer:** The system is not evaluating real accident detection from cameras. Blocker departure, travel to the stop, worsening speed and fully stopped classification are different events. That distinction matters for explaining a replan trigger correctly.

### 10. What is a successful emergency run?

**Short answer:** It requires a valid arrival, not merely the ambulance disappearing from the active list. The final runtime additionally verifies the selected hospital destination and rejects any latched teleport.

**Deeper answer:** Historical classification records arrival/teleport/disappearance outcomes; final integrated lifecycle checks strengthen endpoint assurance. A non-success run has no successful travel-time metric. This prevents an artificial shortcut from appearing fast.

## MEDIUM

### 11. What is the static baseline?

**Short answer:** It creates an initial plan and then does not perform CityBrain post-dispatch replanning. It shares initial inputs with its dynamic pair.

**Deeper answer:** Static does not mean no planning or deliberately choosing the worst route. Its purpose is to isolate the value of later reassessment. Outcomes, including teleports, remain in the success denominator.

### 12. What changes in the dynamic strategy?

**Short answer:** It reevaluates the remaining route as state changes and applies justified alternatives. Stability gates avoid changing route for every small fluctuation.

**Deeper answer:** The historical runner uses an ETA-benefit gate and commitment period. The final runtime uses the structured score-based policy and physical verification before acceptance. I distinguish these configurations when presenting results.

### 13. How many official trials are there?

**Short answer:** There are 120 S05/S07 trials plus 60 official S08 V2 trials, giving 180 unique identities. They form 90 matched static/dynamic pairs.

**Deeper answer:** Each scenario has three profiles, ten seeds and two modes. Exploratory smokes and superseded S08 V1 are not counted again. The total is a validated inventory of two studies rather than a pooled effect size.

### 14. Why use ten random seeds?

**Short answer:** Multiple seeds expose variability in SUMO's stochastic traffic realization. Ten per cell is more informative than presenting only a favourable run.

**Deeper answer:** Equal seeds are paired across strategies. This controls initial stochastic conditions but does not eliminate uncertainty or make the network representative of a real city. Larger seed and scenario samples would strengthen inference.

### 15. Was dynamic given easier traffic?

**Short answer:** I checked equivalent scenario/profile/seed identities and byte-identical generated route inputs within every pair. The intended treatment difference is post-dispatch reassessment.

**Deeper answer:** A route intervention can change subsequent vehicle interactions, so later trajectories need not remain identical. That is an effect of the treatment rather than evidence of unequal initial demand. Provenance and matched inputs make the comparison auditable.

### 16. What is emergency travel time?

**Short answer:** It is valid ambulance arrival time minus dispatch time, in simulated seconds. It is unavailable for teleports and other failures.

**Deeper answer:** Response time in this runner uses the configured 300-second incident reference instead. Neither should be confused with wall-clock runtime. The model does not evaluate full clinical response or pickup duration.

### 17. What is ETA error?

**Short answer:** The recorded error is the absolute difference between successful travel time and the initial ETA. It measures the accuracy of the dispatch prediction.

**Deeper answer:** The initial ETA uses observed edge costs and is not a calibrated arrival predictor. S08 shows substantial initial error, so successful routing does not automatically establish accurate ETA prediction. Failed runs cannot supply the same arrival-based error.

### 18. What did S05 show?

**Short answer:** Dynamic completed 30/30 official runs while static completed 12/30. Successful travel times were 34 seconds, so the primary observed difference is reliability.

**Deeper answer:** In the final smoke, the 311-second reroute occurred while E7 was highly congested but not flagged fully blocked. The alternative had a sufficiently lower score after commitment. I therefore avoid saying that fully stopped E7 necessarily triggered that change.

### 19. What did S07 show?

**Short answer:** All runs succeeded, but static mean travel increased across demand profiles while dynamic remained 34 seconds. Static means were 53.0, 78.6 and 85.1 seconds.

**Deeper answer:** Ten jointly successful pairs support a descriptive timing comparison per profile. Means conceal seed variation; normal static median was only 34 seconds. The result applies to the engineered queue scenario, not all congestion.

### 20. What did S06 show?

**Short answer:** The integrated runtime reported NO_ROUTE around 316 seconds when observed blockages cut off the hospital. It produced no false arrival or travel-time success value.

**Deeper answer:** Independent graph reachability corroborated the cut from the current E5 position. S06 lacks the extended northern bypass used by S08. The conclusion is conditional on current blockages, not that the hospital can never become reachable later.

## HARD

### 21. What proves repeated replanning rather than two route requests?

**Short answer:** Evidence links each accepted revision to its predecessor and shows physical command/read-back before acceptance. Later evaluation uses accepted P1 before proposing P2.

**Deeper answer:** Counting setRoute calls alone is insufficient because calls can fail or repeat the same route. The final runtime verifies the actual remaining suffix. Historical S08 audits separately validate all 50 applied changes against saved movement and route evidence.

### 22. How common was P2 in the S08 research study?

**Short answer:** Twenty of thirty dynamic trials applied two changes, while ten applied one. Normal/heavy/peak two-change counts were 4, 8 and 8 out of ten.

**Deeper answer:** No trial applied more than two changes and no dynamic trial applied zero. Repeated replanning exists across demand profiles, but is not forced for every seed. That is more informative than selecting one dramatic run.

### 23. Was the S08 bypass hard-coded?

**Short answer:** The historical study explicitly supplied a fifth candidate route in its experiment runner. The final integrated runtime's demonstration discovers a bypass through generic topology fallback.

**Deeper answer:** These are distinct candidate-generation contracts and must not be conflated. Both can provide repeated-replan evidence, but the study does not prove unrestricted route discovery. The final demonstration is not a replacement for the multi-seed dataset.

### 24. Why does historical P2 timing differ from the integrated smoke?

**Short answer:** The historical runner and final structured runtime use different gate semantics. Their observed second-application times should therefore be reported separately.

**Deeper answer:** Historical second applications occurred around 320–321 seconds, while the integrated catalogue smoke accepts P2 at 316. The later runtime has score-based policy and invalid-route override, whereas the study used ETA thresholds. Matching a route does not imply identical decision timing.

### 25. What is replanning latency here?

**Short answer:** It is simulation time from an eligible meaningful candidate to its application or acceptance. It is not planner CPU execution time.

**Deeper answer:** The research CSV's general latency field records the first application; S08 also records ordinal and per-application values. Its mean 1.02 seconds uses 50 applications as the denominator. Wall-clock planner computation is a separate millisecond metric.

### 26. How is route oscillation controlled?

**Short answer:** The final runtime requires a material score improvement, commitment period and cooldown for normal valid-route changes. Invalid-route override allows necessary changes despite those timing gates.

**Deeper answer:** Defaults are five score units, ten seconds commitment and five seconds cooldown. This reduces sensitivity to small fluctuations but is not a mathematical proof against all oscillation. Rapid invalidity changes and noisy inputs remain limitations.

### 27. Why verify a travelled suffix rather than the complete route?

**Short answer:** SUMO can retain already-travelled route prefixes in its returned route. The intended action concerns the route remaining from the current physical edge and index.

**Deeper answer:** Exact active-suffix equality rejects partial overlaps and extra destination edges. Already-travelled blocked edges should not invalidate the remaining route. Applying routes on incompatible internal junction positions is deferred.

### 28. How can ten out of ten successes still be uncertain?

**Short answer:** A finite sample does not establish a success probability of one. The approximate per-cell 95% Wilson interval for 10/10 is 72.2–100%.

**Deeper answer:** The interval describes binomial sampling uncertainty under its assumptions, not uncertainty over untested cities or topologies. Shared scenario structure creates additional external-validity limitations. More diverse scenarios are as important as more seeds.

### 29. How did you protect reproducibility?

**Short answer:** I retained trial identities, input files, generating revisions, hashes, checkpoints and decision evidence. Paired inputs and aggregate/checkpoint agreement are audited.

**Deeper answer:** S08 V2 checks results and event hashes plus network/config/demand provenance. Exact reproduction requires the generating implementation and compatible simulator environment. A later documentation or integration commit should not be silently substituted for a historical generating revision.

### 30. Why preserve S08 V1 if V2 is official?

**Short answer:** V1 preserves the original outcomes and the reason for the evidence correction. V2 fixes infinity serialization and resume auditing without silently rewriting V1.

**Deeper answer:** The six compared simulation outcome fields match across all 60 identities. However, the versions are not independent replications and must not be pooled. Retaining superseded evidence makes the research history transparent.

## FACULTY-TRICK

### 31. Does a disappearing ambulance mean it reached the hospital?

**Short answer:** No; disappearance can reflect teleportation or another removal. Success requires arrival evidence and, in the final runtime, the accepted hospital endpoint.

**Deeper answer:** SUMO can temporarily remove a vehicle and later reinsert it during teleport handling. CityBrain latches teleport as a terminal failure, preventing a later arrival from erasing the invalid journey. This avoids falsely short emergency travel times.

### 32. Why not disable teleportation and call all runs successful?

**Short answer:** Disabling a simulator recovery mechanism does not create a valid physical arrival. It would change the experiment rather than justify a success claim.

**Deeper answer:** A vehicle might then wait until timeout instead of teleporting. Either outcome remains a failure to complete within the evaluation contract. The official parameters are preserved so results are comparable.

### 33. Can you claim a 100% reduction in S08 static travel time?

**Short answer:** No; static S08 has no successful arrivals, so its successful travel-time mean is unavailable. The observed comparison is success versus teleport, not a valid percentage timing reduction.

**Deeper answer:** Substituting zero, timeout or teleport duration for a successful journey changes the metric. There are zero jointly successful pairs. Reliability and conditional timing need separate reporting.

### 34. Did dynamic always make S05 faster?

**Short answer:** No; jointly successful static/dynamic pairs have zero measured travel-time difference. Dynamic improved the observed completion rate.

**Deeper answer:** Comparing only successful means would hide the static failures, while saying “faster” would misdescribe the result. I present both denominators and conditional travel time. Reliability is a legitimate but different benefit.

### 35. Does peak demand guarantee worse outcomes than normal?

**Short answer:** No; it increases scheduled demand, not every realized delay monotonically. Signals, insertion and interactions can produce seed-specific outcomes.

**Deeper answer:** The profile labels define controlled inputs. Measured counts, waiting and travel outcomes establish what happened. A plausible expected trend is not a substitute for observed evidence.

### 36. Does emergency vClass mean traffic lights turn green?

**Short answer:** No; this implementation records signal recommendations as advisory. It does not implement CityBrain physical signal-phase control.

**Deeper answer:** Ordinary SUMO signals continue operating. A safe priority system would require explicit phase timing, conflict handling and restoration contracts. Those are future work, not hidden functionality demonstrated by the GUI.

### 37. Does this validate real accident detection?

**Short answer:** No; incidents are prescribed synthetic vehicles and stops. We evaluate routing response to represented changes, not image or sensor detection accuracy.

**Deeper answer:** Real detection would need labelled data, error analysis and uncertain observations. The existing blocker classification has direct access to simulator type/speed or stopped state. That simplifies the upstream perception problem deliberately.

### 38. Can you deploy this in Chennai tomorrow?

**Short answer:** No; the evidence is from simplified synthetic networks and fixed scenarios. Live feeds, calibration, operational safety and real-world validation are missing.

**Deeper answer:** Larger OSM-derived networks, GPS/hospital integration, sensitivity studies and multi-emergency testing are possible next research stages. Software success in SUMO does not authorize control of real traffic infrastructure. Hardware integration remains future work.

### 39. What happens if the dashboard or its storage fails?

**Short answer:** The dashboard is a separate reader with no runtime command path, so stopping it does not stop CityBrain. Evidence failures are already isolated by the frozen exception-safety hotfix.

**Deeper answer:** Missing telemetry makes the display incomplete or stale, not authoritative. It explicitly cannot certify live TraCI connectivity or observe a failure that never reached disk. The dashboard presents decisions; it never selects routes or changes policy.

### 40. Did you personally implement the whole planner and Core?

**Short answer:** No; Subhashini authored the planner/agents and Argh authored the original canonical Core/executor. My main ownership is the simulation and experimental evaluation, with additional integration and exception-safety contributions recorded in Git.

**Deeper answer:** I can explain how the components interact without claiming teammates' work as mine. The per-file contribution map distinguishes original authorship, porting and later modifications. Accurate attribution strengthens the individual contribution report.
