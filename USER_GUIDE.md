# DataPlatformUI user guide

This guide covers local setup, reviewing governed diagnostic products, and using
the guided DataPlatform commands.

## 1. Prepare the UI

Open PowerShell in the DataPlatformUI repository and create its virtual
environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` so `DATALAB_PLATFORM_PATH` identifies the DataPlatform repository:

```dotenv
DATALAB_PLATFORM_PATH=D:\Data Lab\DataPlatform
```

DataPlatform normally stores governed products in
`<DataPlatform>/local-data`. If `DATA_PLATFORM_STORAGE_ROOT` is set when running
DataPlatform, give the UI the same value:

```dotenv
DATA_PLATFORM_STORAGE_ROOT=D:\path\to\diagnostic-data
```

The UI reads the `raw`, `processed`, `curated`, and `metadata` areas beneath that
storage root. It does not connect to cloud or remote storage.

## 2. Start and stop the console

Start the app from the DataPlatformUI repository root:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address printed by Streamlit, normally
`http://localhost:8501`. Stop the server with `Ctrl+C` in the terminal where it
is running.

## 3. Select an observation

Use the **Observation** selector in the sidebar. Each option combines the
business observation date and `snapshot_id` so the pages always refer to an
explicit canonical observation.

If no observation is listed:

1. confirm both environment paths;
2. confirm the storage root contains
   `metadata/snapshots/<snapshot_id>/snapshot.json`;
3. refresh the browser; or
4. use **Run the lab** to inspect and assess staged test evidence.

## 4. Review diagnostic products

### Workspace

Use the workspace for an observation-level summary. It shows the number of
canonical datasets, deterministic Findings, and capabilities assessed as fit,
followed by the highest-priority available Findings.

No Findings does not prove that the portfolio is healthy. It means only that no
condition was emitted by the completed deterministic rules represented in the
selected product.

### Evidence & fitness

This page answers whether the evidence can support each diagnostic capability.
Review:

- blocking structural conditions;
- caveats that limit confidence or coverage;
- rules that could not run; and
- the separate status for each capability.

Poor delivery performance is not itself a data-fitness failure.

### Findings

Filter Findings by domain and severity. Expand a Finding's evidence section to
inspect:

- the rule that produced it;
- deterministic evidence values;
- affected project, task, resource, or other entity IDs; and
- supporting CSV artifacts retained in governed storage.

If a supporting artifact is missing or unreadable, the page reports it as
unavailable rather than hiding the limitation.

### History

The comparison tab presents movement between two observations. The trend tab
presents movement across an ordered observation window and exposes the recorded
continuity policy.

History is optional. A point-in-time diagnosis remains usable without preserved
historical observations.

### Interpretations

This page lists recorded interpretation sessions and their source product,
review status, and latest revision. Interpretations remain distinct from the
deterministic Findings they cite.

## 5. Run the lab

The operation page launches DataPlatform's existing Python modules with the
configured DataPlatform repository as their working directory. Output appears in
the page when each synchronous command completes.

Use this page only with test evidence or evidence handled under the appropriate
client controls.

### Step 1 — Understand the evidence

Place source files in the configured `raw` storage area, then select
**Inspect staged evidence**. DataPlatform creates a technical `run_id`, discovers
the supplied datasets, and profiles the evidence.

### Step 2 — Assess and canonicalise

Select a run whose status is `awaiting_assessment`, enter the business
observation date represented by the evidence, and select **Assess evidence**.

The observation date is not the technical run time. Assessment canonicalises the
run, evaluates structural fitness by capability, and registers a `snapshot_id`.

### Step 3 — Diagnose

Select the canonical observation and choose **Run diagnosis**. DataPlatform runs
eligible diagnostic domains and saves deterministic Findings and their evidence
against that explicit snapshot.

When a capability is not fit, it is skipped by default. Select a displayed
override only when you deliberately accept that named capability's evidence
limitation. An override does not change the stored fitness result and does not
weaken other capabilities.

The operation page does not preserve history automatically. Preservation and
historical analysis remain deliberate DataPlatform activities.

## 6. Use synthetic review data

For a safe interface walkthrough, configure a disposable storage root and run:

```powershell
.venv\Scripts\python.exe -m services.demo
```

The command writes fixed synthetic identifiers `demo-run-001` and
`demo-2026-08-31`, including example fitness, Findings, and supporting CSVs.
Because those fixed paths are replaced on repeated runs, do not run the demo
against client storage.

Restart or refresh the console, then choose the synthetic observation in the
sidebar.

## Troubleshooting

### The configured platform path does not exist

Correct `DATALAB_PLATFORM_PATH` in `.env`. It must name the DataPlatform
repository directory, not its `local-data` directory.

### No observations are available

Check `DATA_PLATFORM_STORAGE_ROOT` and verify that assessed snapshot metadata
exists. An inspected run does not become selectable as an observation until
assessment registers its snapshot.

### No runs are awaiting assessment

Run **Inspect staged evidence** first. Runs already assessed are intentionally
excluded from the assessment selector.

### A guided command fails

Expand the command status and read its captured output. The UI reports the
DataPlatform command's exit code and message; it does not reinterpret or suppress
platform failures. Also confirm the UI dependencies were installed from the
current `requirements.txt`.

### Supporting evidence is unavailable

Confirm the referenced file still exists beneath the configured governed storage
root. The UI rejects artifact paths that escape the `raw`, `processed`,
`curated`, or `metadata` areas.

## Data handling boundary

The review pages are read-only. The **Run the lab** page is not: it invokes
DataPlatform commands that create derived evidence and metadata in the configured
storage root. The UI does not modify raw source files, calculate its own Findings,
or produce AI interpretations.
