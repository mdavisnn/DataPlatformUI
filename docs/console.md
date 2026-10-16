# Data Lab console

The console provides two capabilities over DataPlatform's existing governed
products and commands.

## Release 1 — Review

The Review navigation exposes canonical observations, capability-specific
fitness, deterministic Findings, their supporting evidence, historical
comparisons and trends. Related evidence is grouped into four paired
destinations: Workspace, Projects & findings, Schedule & plan, and Structure &
patterns. Each destination renders only its selected view. Interpretations are
not exposed until that workflow is implemented.

The **Workspace** destination combines the executive Overview with Evidence &
fitness. Its Overview presents four decision-oriented measures, a compact
coverage summary, the governed portfolio attention map and a short priority
signal rail. Secondary Finding distributions are available on demand. The
**Projects & findings** destination combines the saved Project health matrix
with All findings. All findings puts its selectable index and detail view
before optional distribution charts, keeping persisted rule context, evidence
facts, affected entities, supporting artifacts and capability fitness visibly
distinct.

The **Schedule & plan** destination combines the DCMA 14-Point Schedule
assessment with Plan on a page. The plan view is a point-in-time presentation
over one selected snapshot. It groups project forecast bars by portfolio and
supports project task drill-down. It overlays existing Findings only when their
governed supporting evidence contains usable dates; it does not calculate
Findings or infer dates.

The **Schedule assessment** and **Resources** views consume named products
recorded on their successful diagnostic outcomes. Schedule uses the saved DCMA
project rollup, one result per project and metric, task or dependency conditions
and the activity profile. Its Portfolio overview, Metric detail and Activity
evidence perspectives arrange those products without creating a composite
score. Resources uses resource and project rollups, dated assignment evidence,
conflict periods and unassigned work. Its Summary, By person and By project
perspectives only arrange these saved products. Both pages expose
backend-recorded coverage, assumptions and unavailable measures; the console
does not recreate rule flags, allocation pressure or coverage calculations.

The **Evidence & fitness** view combines capability summaries with their saved
row-level fitness evidence to show descriptive rule names, affected fields and
plain-English explanations. It does not change capability status.

The **Structure & patterns** destination combines Dependencies and Patterns.
Dependencies consumes saved edge, task-connectivity and project
coverage products, including backend-calculated bridges, articulation points
and cycles. Patterns consumes long-form observations, distribution
summaries and IQR-based interestingness evidence. Network placement, percentile
ranks, fences and unusualness flags are therefore not recalculated in the UI.
Friendly measure names, explanations and the glossary describe those saved
values; interactive controls only narrow or arrange the evidence.

The **History** destination presents one selected governed product at a time.
Trend windows show saved observation and transition counts, continuity policy,
forecast-finish trajectories, historical Findings and evidence-fitness limits.
The portfolio trajectory is primary; a single-project inspection is revealed
only when requested. Historical Findings use the same compact priority-signal
treatment as the executive Overview.
Two-observation comparisons show the same identity and comparability context
beside their saved change evidence. The UI does not declare observations
comparable beyond the recorded contract, bridge absent projects, introduce a
materiality threshold, or interpret why movement occurred.

## Release 2 — Operate

The **Run the lab** page presents the existing consultant sequence as one
active operational stage with current readiness and governed-product counts.
The first actionable stage opens automatically; completed earlier stages stay
selectable:

1. place evidence in the client's configured `raw/<client_id>/` inbox;
2. inspect and profile the evidence;
3. assess the inspected run for an explicit business observation date;
4. diagnose the resulting canonical snapshot.

Not-fit overrides remain explicit and capability-scoped. The UI launches the
existing `lab` modules in the configured DataPlatform repository; it does not
reimplement processing or diagnostic rules.

Run ID, business observation date and snapshot ID are labelled separately
throughout the workflow. Actions remain synchronous and user-triggered; the
visual stage treatment does not introduce background orchestration.

The UI environment includes DataPlatform's tabular runtime dependencies because
the operation page launches those modules with the UI's Python interpreter.

## Deterministic scenario planning

The optional **Scenario planning** page is a control and review surface over
the separate SchedulePlatform repository. It builds the published strict V1.1
JSON configuration, including an explicit inclusive planning horizon, from
consultant inputs and invokes the
schedule_platform.cli generate command. SchedulePlatform owns validation,
baseline assessment, candidate generation, feasibility, ranking and the
isolated output package. DataPlatformUI reads those saved products and performs
only presentation transforms.

The command runs through `SCHEDULE_PLATFORM_PYTHON`, normally the scheduling
repository's own virtual environment. The page first executes the CLI version
check with the same interpreter, working directory and `PYTHONPATH`, so missing
scheduling dependencies are reported before a consultant submits the form. The
UI does not install or import the scheduling engine's solver dependencies.

CP-SAT is protected by an explicit integration gate. The console requires a
published V1.1 backend selector, a public `generate --backend cp-sat` command,
and a valid `generation_result_v1.schema.json` containing backend, solver,
settings and authoritative-validation provenance. The current SchedulePlatform
checkout does not publish those integration contracts, so the UI offers only
bounded deterministic generation even though internal CP-SAT classes exist.

The planning form is one programmatically collapsible section so generated
results remain close to the top of the page. Result adapters align baseline and
scenario resource-load intervals around the periods that changed, identify
changed assignments and summarise overload and finish-movement effects. These
are display calculations over the saved package; they do not alter ranking or
create diagnostic Findings. The result surface also presents the validated 1.1
contract, horizon, bounded-search limits, configuration fingerprint and saved
engine/rule versions. Horizon-exceeded constraint evidence is promoted to an
actionable result-level message.

Scenario packages are keyed to one client and source snapshot but are not
written into DataPlatform storage. They are hypothetical planning artefacts,
not canonical observations, diagnostic Findings or historical evidence.

## Synthetic review data

`python -m services.demo` stages five synthetic v2 datasets for `demo-ui` and
creates a genuine observation through DataPlatform's inspection, assessment
and diagnosis commands. It does not hand-write governed metadata or Findings.
`python -m services.demo --reset` first removes only `demo-ui` and the legacy
`demo-001` fixture from local DataPlatform and SchedulePlatform roots. V1.0
synthetic scenario packages are reset rather than migrated.

## Prototype boundary

This is a local consultant interface. It does not provide authentication,
client segregation, background jobs, cloud storage, or production deployment.
Long-running actions execute synchronously in the active Streamlit session.

The navigation is followed by a global **Data scope** sidebar section. Its
Client and Observation selectors apply to every destination.
