# Data Lab console

The console provides two capabilities over DataPlatform's existing governed
products and commands.

## Release 1 — Review

The Review pages expose canonical observations, capability-specific fitness,
deterministic Findings, their supporting evidence, historical comparisons and
trends, and recorded interpretations. Findings remain visibly distinct from
consultant interpretation.

## Release 2 — Operate

The **Run the lab** page follows the existing consultant sequence:

1. stage evidence in DataPlatform's configured `raw` storage area;
2. inspect and profile the evidence;
3. assess the inspected run for an explicit business observation date;
4. diagnose the resulting canonical snapshot.

Not-fit overrides remain explicit and capability-scoped. The UI launches the
existing `lab` modules in the configured DataPlatform repository; it does not
reimplement processing or diagnostic rules.

The UI environment includes DataPlatform's tabular runtime dependencies because
the operation page launches those modules with the UI's Python interpreter.

## Synthetic review data

`python -m services.demo` writes synthetic governed products beneath the
configured storage root. It does not contain client data.

## Prototype boundary

This is a local consultant interface. It does not provide authentication,
client segregation, background jobs, cloud storage, or production deployment.
Long-running actions execute synchronously in the active Streamlit session.
