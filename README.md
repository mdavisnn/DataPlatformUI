# DataPlatformUI

DataPlatformUI is the local Streamlit review interface for the DataPlatform PPM
diagnostic and historical analysis lab. It presents governed observations,
fitness assessments, deterministic Findings, historical products and recorded
human interpretations without recalculating them.

The repositories have separate responsibilities:

- **DataPlatformUI** owns presentation, navigation and read-only access to local
  governed products.
- **DataPlatform** owns client evidence, canonicalisation, fitness, diagnostic
  rules, Findings, history and interpretation records.

The UI does not infer causes, calculate Findings or merge interpretation with
deterministic evidence.

## Current status

The sidebar first selects a client, then an observation belonging to that
client. Review pages scope runs, snapshots, comparisons, trends and
interpretations to the selected `client_id` before displaying them.

The **Run the lab** page passes the selected `client_id` when inspection
begins. Assessment and diagnosis pass only the run or snapshot identity, from
which DataPlatform resolves client ownership. The page remains a local,
consultant-facing control surface rather than a production orchestration layer.

## DataPlatform contract

Every run and observation belongs to a stable `client_id`. Use lowercase
letters, numbers, hyphens or underscores, for example `client-001`.

The canonical schema is version 2 and supports five related datasets:

- projects;
- tasks;
- resources;
- assignments;
- dependencies.

`run_id`, `observation_date` and `snapshot_id` have different meanings:

- `run_id` identifies a technical processing execution;
- `observation_date` is the business date represented by the evidence;
- `snapshot_id` identifies the immutable canonical observation.

History is optional. A snapshot can be diagnosed without being preserved.

## Requirements

- A local checkout of DataPlatform.
- Python and `pip`.
- Local DataPlatform storage, normally `<DataPlatform>/local-data`.

Create the UI environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure the DataPlatform repository:

```dotenv
DATALAB_PLATFORM_PATH=D:\Data Lab\DataPlatform
```

If DataPlatform uses a different governed storage root, configure the same root
for the UI:

```dotenv
DATA_PLATFORM_STORAGE_ROOT=D:\path\to\diagnostic-data
```

`.env` and `.streamlit/secrets.toml` are excluded from source control.

## Run the console

From the DataPlatformUI repository root:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit normally opens `http://localhost:8501`.

Use **Exit Data Lab** at the bottom of the sidebar to stop the local Streamlit
server gracefully and return control to the launching terminal. This stops the
whole local console, including any other open browser sessions; closing a
browser tab alone does not stop the server.

## Prepare DataPlatform evidence

From the DataPlatform repository, place each client's source files directly in
its raw inbox:

```text
local-data/raw/client-001/projects.csv
local-data/raw/client-001/tasks.csv
local-data/raw/client-001/resources.csv
local-data/raw/client-001/assignments.csv
local-data/raw/client-001/dependencies.csv
```

Then run the governed workflow:

```powershell
python -m lab.inspect --client-id client-001
python -m lab.assess --run-id <run_id> --observation-date <YYYY-MM-DD>
python -m lab.diagnose --snapshot-id <snapshot_id>
```

Inspection profiles only supported files directly beneath the selected
client's raw inbox, then archives the exact successful run sources.

Refresh the UI after the commands complete. Select the client and then the
resulting observation from the sidebar.

## Console pages

- **Workspace** presents the backend-produced executive snapshot, diagnostic
  coverage, evidence limitations and priority Findings.
- **Evidence & fitness** separates structural fitness, blockers, caveats and
  unavailable rules from delivery conditions.
- **Findings** shows deterministic conditions, affected entities, rules and
  supporting governed evidence.
- **Project health** compares projects across separate backend-produced
  portfolio, schedule, resource, reporting and dependency dimensions.
- **Schedule** reads backend-produced project, activity and condition products
  to show overdue work, milestone position, duration distribution and schedule
  evidence coverage. Missing float, criticality or hierarchy evidence remains
  visibly unavailable.
- **Resources** reads backend-produced resource and project rollups, conflict
  periods and unassigned work. Planned allocation pressure is kept distinct
  from actual utilisation and unsupported capacity forecasts.
- **Plan on a page** groups canonical project forecast bars by portfolio for
  the selected snapshot. Filter to one portfolio, then select a project bar or
  use the project picker to drill into its task schedule. Both levels overlay
  only Findings whose supporting evidence provides defensible dates; undated
  Findings remain visible beside the timelines.
- **History** displays existing two-observation comparisons and an interactive
  delivery trajectory for governed trend windows. The trajectory shows
  forecast-finish movement with reported RAG context and project drill-down,
  while retaining the underlying governed evidence on demand.
- **Interpretations** lists recorded human interpretation sessions separately
  from deterministic products.
- **Run the lab** provides prototype controls for inspection, assessment and
  diagnosis. Client identity is supplied only when inspection begins;
  downstream ownership is resolved from the run or snapshot metadata.

## Optional history and interpretation

Use DataPlatform to preserve and compare observations from the same client:

```powershell
python -m lab.preserve --snapshot-id <snapshot_id>
python -m lab.compare --from-snapshot <earlier_id> --to-snapshot <later_id>
python -m lab.trends --from-snapshot <earliest_id> --to-snapshot <latest_id>
```

Prepare and record a human-authored interpretation with `lab.interpret`. See
[USER_GUIDE.md](USER_GUIDE.md) for the complete workflow.

## Synthetic review data

Create the synthetic `demo-ui` observation from packaged v2 evidence:

```powershell
.venv\Scripts\python.exe -m services.demo
```

The command stages all five canonical datasets, then uses DataPlatform's real
inspection, assessment and diagnosis commands. The result is a genuine
point-in-time observation dated `2026-08-31`, with backend-produced fitness,
Findings and lineage. It is not preserved for history automatically.

The fixed demo is safe to rerun: an existing completed observation is reused,
and changed files already present in `raw/demo-ui` are never overwritten.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Prototype boundary

The console is local and consultant-facing. It does not provide authentication,
authorisation, cloud storage, background jobs, workflow orchestration or
production deployment. DataPlatform enforces client identity and historical
comparability. UI client filtering keeps review state coherent, but it is not
an authentication or authorisation boundary.

See [USER_GUIDE.md](USER_GUIDE.md) for operating instructions and
[docs/console.md](docs/console.md) for the release boundary.
