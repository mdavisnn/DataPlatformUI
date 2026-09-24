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

Place source files directly beneath that client's raw inbox:

```text
local-data/raw/client-001/projects.csv
local-data/raw/client-001/tasks.csv
local-data/raw/client-001/resources.csv
local-data/raw/client-001/assignments.csv
local-data/raw/client-001/dependencies.csv
```

CSV and supported Excel files may be used. The canonical v2 model contains five
datasets, but DataPlatform will assess the evidence actually supplied and expose
missing evidence through capability fitness.

## 3. Create a canonical observation

### Inspect one client

Inspect only the intended client's raw-inbox evidence:

```powershell
python -m lab.inspect --client-id client-001
```

Inspection discovers and profiles supported inbox files without changing their
contents. After profiling succeeds, it archives the exact evidence beneath the
client's immutable run path. Keep the returned run ID for assessment.

### Assess the run

Use the business date represented by the evidence, not the technical processing
date:

```powershell
python -m lab.assess --run-id <run_id> --observation-date <YYYY-MM-DD>
```

Assessment canonicalises the evidence, evaluates fitness by capability and
registers an immutable `snapshot_id`.

### Diagnose the snapshot

```powershell
python -m lab.diagnose --snapshot-id <snapshot_id>
```

Diagnosis runs each eligible deterministic domain and stores:

- `fitness.json`;
- `diagnosis.json`;
- `findings.json`;
- `diagnostic_summary.md`;
- supporting CSV evidence beneath
  `curated/<client_id>/snapshots/<snapshot_id>/`.

A result of `PASS WITH LIMITATIONS` means eligible diagnostics completed with
recorded fitness caveats. It is not the same as a failed diagnosis.

When a capability is not fit, it is skipped by default. Only acknowledge a
known limitation deliberately:

```powershell
python -m lab.diagnose --snapshot-id <snapshot_id> --allow-not-fit resource
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

The workspace presents the backend-produced executive summary: portfolio scale,
diagnostic coverage, evidence limitations, exception concentration and priority
Findings. No Findings does not prove that a portfolio is healthy.

### Evidence & fitness

Review each capability separately:

- blocking structural conditions;
- caveats affecting confidence or coverage;
- unavailable rules;
- overall capability status.

Expand a capability to see a descriptive rule name, the affected dataset and
field, the number of occurrences and a short plain-English explanation. The
stable rule ID remains visible for traceability. Missing datasets and analyses
that could not run are explained separately.

Poor delivery performance is not itself a structural fitness failure.

### Findings

Filter deterministic Findings by domain and severity. Expand a Finding to see
its rule, evidence values, affected entity IDs and supporting governed CSVs.

### Project health

Compare projects across separate diagnostic lenses. `No finding` means that a
capability completed without producing a Finding for that project.
`Not assessed` means the capability did not run or is not implemented. Select
a project to inspect the authoritative Finding IDs behind the matrix row.

### Schedule

Review backend-calculated overdue activities and milestones, project condition
concentration, activity duration distribution, and schedule evidence coverage.
Use the project and health filters to narrow the saved products. Total float,
criticality, hierarchy, baseline variance and historical milestone slippage are
shown as unavailable when the observation cannot support them.

The Schedule page does not infer critical paths or recalculate the schedule
rules. Use **Plan on a page** when you need the detailed dated project and task
timeline.

### Resources

Choose one of three perspectives:

- **Summary** reviews portfolio-wide allocation pressure, shared people and
  over-allocation conflict periods.
- **By person** provides a plan-on-a-page timeline across projects. Assignment
  dates take precedence; missing endpoints visibly fall back to task forecast
  dates. Green means no calculated conflict, Amber means a conflict below the
  configured high threshold, and Red means the overlapping allocation meets
  or exceeds that threshold. Project identity remains in labels and tooltips.
- **By project** compares assignment coverage, people, shared people, conflicts
  and unassigned tasks across projects, then provides project detail.

Allocation percentages describe planned assignments. They are not actual
utilisation, timesheet effort or a time-phased forecast. The page displays the
configured conflict threshold, capacity evidence coverage and unsupported
measures explicitly.

### Dependencies

Review linked-task coverage, cross-project links, high-connectivity tasks,
bridge links, articulation points and directed cycles. The network uses stable
coordinates saved by DataPlatform. Node size reflects backend-calculated
connectivity; filters only narrow the displayed evidence.

Structural concentration does not establish risk. Unlinked tasks may be valid
schedule starts, finishes or summary activities, so dependency coverage remains
visible evidence rather than a standalone health grade.

### Patterns

Choose a project or resource measure to review its saved distribution and
ranked evidence. Dropdown labels use consultant-friendly names and the selected
measure's definition appears immediately beneath the controls. Expand
**Measure glossary** to review every available definition. The distribution
evidence then shows the backend-produced range, quartiles, IQR fences, coverage
and percentile context before listing values already identified as unusual.

An unusual value means that it differs from peers in the selected observation.
It does not prove poor performance or cause. No composite anomaly or project
health score is calculated.

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

The operation page uses the client selected in the sidebar. **Inspect raw
evidence** calls DataPlatform's client-scoped inspection command, which:

1. discovers supported files directly beneath `raw/<client_id>/`;
2. excludes other clients and archived run evidence;
3. profiles the exact files admitted to the run;
4. archives those files only after inspection succeeds.

Keep the selected client and raw inbox aligned before starting inspection.
Assessment and diagnosis pass only the selected run or snapshot identity;
DataPlatform resolves and validates its client ownership.
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
to overwrite any changed files already present beneath `raw/demo-ui`.

## Troubleshooting

### The configured platform path does not exist

`DATALAB_PLATFORM_PATH` must identify the DataPlatform repository, not its
`local-data` directory.

### No observations are available

Check `DATA_PLATFORM_STORAGE_ROOT` and verify that this exists:

```text
metadata/<client_id>/snapshots/<snapshot_id>/snapshot.json
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
