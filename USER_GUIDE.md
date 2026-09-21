# DataPlatformUI user guide

This guide explains how to prepare client evidence in DataPlatform and review
the resulting governed products in DataPlatformUI.

## 1. Prepare the UI

Open PowerShell in the DataPlatformUI repository:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the DataPlatform repository in `.env`:

```dotenv
DATALAB_PLATFORM_PATH=D:\Data Lab\DataPlatform
```

DataPlatform normally stores governed products beneath
`<DataPlatform>/local-data`. If it uses another storage root, give the UI the
same value:

```dotenv
DATA_PLATFORM_STORAGE_ROOT=D:\path\to\diagnostic-data
```

The UI reads the `raw`, `processed`, `curated` and `metadata` areas. It does not
connect to remote storage.

## 2. Prepare client evidence

Choose a stable lowercase `client_id` containing letters, numbers, hyphens or
underscores. Do not use a display name that may change.

Place the source files beneath that client's staging folder in DataPlatform:

```text
local-data/staged/client-001/projects.csv
local-data/staged/client-001/tasks.csv
local-data/staged/client-001/resources.csv
local-data/staged/client-001/assignments.csv
local-data/staged/client-001/dependencies.csv
```

CSV and supported Excel files may be used. The canonical v2 model contains five
datasets, but DataPlatform will assess the evidence actually supplied and expose
missing evidence through capability fitness.

## 3. Create a canonical observation

### Inspect one client

Inspect only the intended client's staged evidence:

```powershell
python -m lab.inspect --client-id client-001
```

Inspection copies that client's supported files into governed raw storage
without changing their contents, creates a technical `run_id`, then discovers
and profiles only those newly ingested files. Keep the returned run ID for
assessment.

### Assess the run

Use the business date represented by the evidence, not the technical processing
date:

```powershell
python -m lab.assess --client-id client-001 --run-id <run_id> --observation-date <YYYY-MM-DD>
```

Assessment canonicalises the evidence, evaluates fitness by capability and
registers an immutable `snapshot_id`.

### Diagnose the snapshot

```powershell
python -m lab.diagnose --client-id client-001 --snapshot-id <snapshot_id>
```

Diagnosis runs each eligible deterministic domain and stores:

- `fitness.json`;
- `diagnosis.json`;
- `findings.json`;
- `diagnostic_summary.md`;
- supporting CSV evidence beneath `curated/snapshots/<snapshot_id>/`.

A result of `PASS WITH LIMITATIONS` means eligible diagnostics completed with
recorded fitness caveats. It is not the same as a failed diagnosis.

When a capability is not fit, it is skipped by default. Only acknowledge a
known limitation deliberately:

```powershell
python -m lab.diagnose --client-id client-001 --snapshot-id <snapshot_id> --allow-not-fit resource
```

The override is capability-specific and does not change the stored fitness
assessment.

## 4. Start the console

From the DataPlatformUI repository:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address printed by Streamlit, normally
`http://localhost:8501`. Use **Exit Data Lab** at the bottom of the sidebar to
stop the Streamlit server cleanly and return control to the launching terminal.
The button stops all sessions connected to this local console. `Ctrl+C` remains
available as a terminal fallback.

Refresh the browser after creating new DataPlatform products.

## 5. Select and review an observation

Use the **Client** selector in the sidebar first. The **Observation** selector
then shows only snapshots belonging to that `client_id`; each option contains
the business observation date and `snapshot_id`.

Changing client clears the previous observation selection and selects that
client's most recent available observation. Runs, comparisons, trends and
interpretations shown elsewhere in the console are filtered to the same client.

### Workspace

The workspace summarises canonical datasets, deterministic Findings and fitness.
No Findings does not prove that a portfolio is healthy; it only means the
completed configured rules emitted no conditions.

### Evidence & fitness

Review each capability separately:

- blocking structural conditions;
- caveats affecting confidence or coverage;
- unavailable rules;
- overall capability status.

Poor delivery performance is not itself a structural fitness failure.

### Findings

Filter deterministic Findings by domain and severity. Expand a Finding to see
its rule, evidence values, affected entity IDs and supporting governed CSVs.

### Plan on a page

Start with the project summary, where forecast bars are grouped by portfolio
within the currently selected observation. Use **Portfolio** to narrow the
scope, then select a project bar (or use **Drill into project**) to open its
canonical task timeline. Coloured overlays show dated supporting evidence for
deterministic Findings; the blue dashed line is the observation date. The
domain and severity filters apply to both timeline levels.

In the task timeline, select an overlay or use **Inspect finding** to open the
underlying Finding and its dated evidence rows. Projects or tasks with missing
or invalid forecast dates are disclosed instead of plotted. Projects without a
portfolio identifier are grouped under **Unassigned**.

Findings without defensible evidence dates are listed separately rather than
being assigned an inferred position on either plan.

### History

The page displays comparison and trend products that DataPlatform has already
created. History is optional and is not required for point-in-time diagnosis.

### Interpretations

The page lists recorded interpretation sessions. Interpretations remain
separate from deterministic Findings and must cite the Findings they discuss.

## 6. Preserve and compare observations

Preservation is an explicit decision:

```powershell
python -m lab.preserve --snapshot-id <snapshot_id>
```

Only one eligible snapshot per client may represent an observation date. To
preserve a corrected extract for the same client and date:

```powershell
python -m lab.preserve --snapshot-id <corrected_id> --supersedes <original_id>
```

Compare two preserved observations from the same client in business-date order:

```powershell
python -m lab.compare --from-snapshot <earlier_id> --to-snapshot <later_id>
```

Analyse every eligible observation within a longer window:

```powershell
python -m lab.trends --from-snapshot <earliest_id> --to-snapshot <latest_id>
```

Cross-client comparison is rejected. Trend analysis compares adjacent
observations and does not infer continuity across an absent project.

Refresh the UI to review the new comparison or trend product.

## 7. Prepare and record interpretation

Create a working directory from exactly one diagnostic product:

```powershell
python -m lab.interpret prepare --snapshot-id <snapshot_id> --output-dir <directory>
python -m lab.interpret prepare --comparison-id <comparison_id> --output-dir <directory>
python -m lab.interpret prepare --trend-id <trend_id> --output-dir <directory>
```

Edit the generated `interpretation.json`, then record it:

```powershell
python -m lab.interpret record --input <directory>\interpretation.json
```

Interpretive summaries, questions, hypotheses and provisional interventions are
human-authored and must cite valid Finding IDs.

## 8. Run the lab

The operation page uses the client selected in the sidebar. **Inspect staged
evidence** calls DataPlatform's client-scoped inspection command, which:

1. ingests supported files from `staged/<client_id>/` without changing them;
2. excludes other clients and stale raw files from the run;
3. discovers and profiles the exact files just ingested;
4. creates a client-scoped run awaiting assessment.

Keep the selected client and staging folder aligned before starting inspection.
Assessment and diagnosis also pass the selected client to DataPlatform, which
rejects a run or snapshot belonging to another client before writing outputs.
The controls run synchronously and remain intended for local, consultant-led
operation rather than unattended orchestration.

## 9. Synthetic review fixture

```powershell
.venv\Scripts\python.exe -m services.demo
```

This stages synthetic projects, tasks, resources, assignments and dependencies
for `demo-ui`, then runs the real DataPlatform inspection, assessment and
diagnosis workflow. Select `demo-ui` and observation date `2026-08-31` in the
console after it completes.

The generated snapshot has normal backend lineage and can be preserved if you
want to exercise history, although a comparison still requires a second
observation. Rerunning the command reuses the completed fixed demo. It refuses
to overwrite any changed files already present beneath `staged/demo-ui`.

## Troubleshooting

### The configured platform path does not exist

`DATALAB_PLATFORM_PATH` must identify the DataPlatform repository, not its
`local-data` directory.

### No observations are available

Check `DATA_PLATFORM_STORAGE_ROOT` and verify that this exists:

```text
metadata/snapshots/<snapshot_id>/snapshot.json
```

Inspection alone does not create a selectable observation; assessment does.

### No runs are awaiting assessment

Run client-aware inspection from DataPlatform and refresh the UI. Runs already
assessed are intentionally excluded.

### A guided command fails

Read the captured command output and exit status. Confirm that the UI and
DataPlatform use the same storage root. For inspection failures, use the CLI
with an explicit `--client-id`.

### Supporting evidence is unavailable

Confirm that the referenced object exists beneath `raw`, `processed`, `curated`
or `metadata`. The UI rejects paths that escape governed storage.

## Data handling boundary

Review pages are read-only. DataPlatform commands create governed evidence and
metadata. The UI does not modify raw source evidence, calculate Findings or
produce AI interpretations. It is a local prototype without authentication,
authorisation or production deployment controls. Client selection scopes the
local review experience; it is not an access-control mechanism.
