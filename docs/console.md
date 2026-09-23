# Data Lab console

The console provides two capabilities over DataPlatform's existing governed
products and commands.

## Release 1 — Review

The Review pages expose canonical observations, capability-specific fitness,
deterministic Findings, their supporting evidence, historical comparisons and
trends, and recorded interpretations. Findings remain visibly distinct from
consultant interpretation.

The **Plan on a page** prototype is a point-in-time presentation over one
selected snapshot. It first groups project forecast bars by portfolio, supports
portfolio filtering, and lets the consultant select a project to drill into its
task timeline. It reads canonical project and task datasets and overlays
existing Findings only when their governed supporting evidence contains usable
dates. It does not calculate Findings, infer missing dates, or require the
snapshot to be preserved for history.

The **Executive snapshot** and **Project health** pages consume the saved
summary and cross-domain project matrix produced by DataPlatform. The console
does not recreate their counts or classifications from canonical data.

## Release 2 — Operate

The **Run the lab** page follows the existing consultant sequence:

1. place evidence in the client's configured `raw/<client_id>/` inbox;
2. inspect and profile the evidence;
3. assess the inspected run for an explicit business observation date;
4. diagnose the resulting canonical snapshot.

Not-fit overrides remain explicit and capability-scoped. The UI launches the
existing `lab` modules in the configured DataPlatform repository; it does not
reimplement processing or diagnostic rules.

The UI environment includes DataPlatform's tabular runtime dependencies because
the operation page launches those modules with the UI's Python interpreter.

## Synthetic review data

`python -m services.demo` stages five synthetic v2 datasets for `demo-ui` and
creates a genuine observation through DataPlatform's inspection, assessment
and diagnosis commands. It does not hand-write governed metadata or Findings.

## Prototype boundary

This is a local consultant interface. It does not provide authentication,
client segregation, background jobs, cloud storage, or production deployment.
Long-running actions execute synchronously in the active Streamlit session.
