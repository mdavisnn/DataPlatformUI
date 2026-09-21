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

The **Run the lab** page passes the selected `client_id` to DataPlatform.
Inspection ingests only that client's staged files before discovering and
profiling the exact evidence admitted to the run. The page remains a local,
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

## Prepare DataPlatform evidence

From the DataPlatform repository, stage each client's source files in its own
folder:

```text
local-data/staged/client-001/projects.csv
local-data/staged/client-001/tasks.csv
local-data/staged/client-001/resources.csv
local-data/staged/client-001/assignments.csv
local-data/staged/client-001/dependencies.csv
```

Then run the governed workflow:

```powershell
python -m lab.inspect --client-id client-001
python -m lab.assess --client-id client-001 --run-id <run_id> --observation-date <YYYY-MM-DD>
python -m lab.diagnose --client-id client-001 --snapshot-id <snapshot_id>
```

Inspection ingests only the selected client's staged files before discovery and
profiling.

Refresh the UI after the commands complete. Select the client and then the
resulting observation from the sidebar.

## Console pages

- **Workspace** summarises the selected observation and its priority Findings.
- **Evidence & fitness** separates structural fitness, blockers, caveats and
  unavailable rules from delivery conditions.
- **Findings** shows deterministic conditions, affected entities, rules and
  supporting governed evidence.
- **History** displays existing two-observation comparisons and trend windows.
- **Interpretations** lists recorded human interpretation sessions separately
  from deterministic products.
- **Run the lab** provides prototype controls for assessment and diagnosis. Its
  inspection action also performs client-scoped staged-file ingestion. Every
  action passes the selected client to DataPlatform for an ownership check.

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
and changed files already present in `staged/demo-ui` are never overwritten.

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
