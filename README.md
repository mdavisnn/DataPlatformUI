# DataPlatformUI

DataPlatformUI is the local Streamlit review interface for the DataPlatform PPM
diagnostic and historical analysis lab. It presents governed observations,
fitness assessments, deterministic Findings, historical products and recorded
human interpretations without recalculating them. It can also act as an
optional control and review surface for deterministic SchedulePlatform runs.

The repositories have separate responsibilities:

- **DataPlatformUI** owns presentation, navigation and read-only access to local
  governed products.
- **DataPlatform** owns client evidence, canonicalisation, fitness, diagnostic
  rules, Findings, history and interpretation records.

The UI does not infer causes, calculate Findings or merge interpretation with
deterministic evidence.

The shared visual foundation is defined through native Streamlit theme tokens
and presentation components. See
[docs/visual-identity.md](docs/visual-identity.md) before adding new page-level
styles or dashboard primitives.

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
- An optional local checkout of SchedulePlatform for scenario planning.
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

To enable scenario planning, configure the separate SchedulePlatform checkout:

```dotenv
SCHEDULE_PLATFORM_PATH=D:\Data Lab\SchedulePlatform
SCHEDULE_PLATFORM_PYTHON=D:\Data Lab\SchedulePlatform\.venv\Scripts\python.exe
```

Use a SchedulePlatform-owned environment so its scheduling dependencies remain
separate from the UI. For example, create `.venv` in the SchedulePlatform
checkout and install that project there. If `SCHEDULE_PLATFORM_PYTHON` is not
set, the UI looks for that local `.venv` before trying its own interpreter. The
scenario form is enabled only when the chosen interpreter can run
`python -m schedule_platform.cli --version` successfully.

Scenario results default to SchedulePlatform/output. To use another local
root, set SCHEDULE_PLATFORM_OUTPUT_ROOT. The output root must not overlap
DataPlatform evidence or schemas.

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

- **Workspace** combines an Overview with Evidence & fitness. The Overview
  opens with four decision-oriented measures: projects, Findings, projects
  affected and evidence fitness. A compact coverage summary then gives way to
  the portfolio attention map and a short priority-signal rail. Finding
  distributions remain available on demand rather than competing with the
  main review path. Evidence & fitness separates structural blockers, caveats
  and unavailable rules from delivery conditions.
- **Projects & findings** combines Project health with All findings. Project
  health compares projects across separate backend-produced portfolio,
  schedule, resource, reporting and dependency dimensions without creating an
  overall score. All findings places the selectable Finding and its governed
  evidence before optional distribution charts, keeping deterministic
  conditions, affected entities and rule context in one master-detail flow.
- **Schedule & plan** combines the DCMA 14-Point Schedule assessment with Plan
  on a page. Schedule assessment presents the saved project-by-metric matrix,
  tripwire results, unavailable metrics, supporting conditions, durations and
  evidence coverage without calculating a composite score. Plan on a page
  groups canonical project forecast bars by portfolio, supports project
  drill-down and overlays only Findings with defensible dates.
- **Resources** provides Summary, By person and By project perspectives over
  backend-produced resource products. The person plan-on-a-page uses assignment
  dates first, labels task-forecast fallbacks and uses backend-produced
  Green/Amber/Red conflict status. Project comparisons remain distinct from
  actual utilisation and unsupported capacity forecasts.
- **Structure & patterns** combines Dependencies with Patterns. Dependencies
  shows saved coverage, cross-project coupling, hubs, bridges, articulation
  points and cycles. Patterns presents saved distributions, percentile context
  and values outside configured IQR fences without treating unusualness as
  proof of poor performance.
- **History** provides a focused trend-window or two-observation workspace.
  Portfolio trajectory is the default analytical focus; individual project
  inspection is available on demand. Observation dates and snapshot IDs remain
  visible beside saved fitness caveats, the comparability contract, recorded
  historical Findings and row-level change evidence. Continuity breaks remain
  visible and significance is left to consultant interpretation.
- **Scenario planning** creates a strict SchedulePlatform V1.1 configuration
  for the selected snapshot, including an explicit inclusive planning horizon,
  then runs bounded deterministic generation and reads the saved client-scoped
  result package. Its collapsible configuration gives way
  to ranked options with separate resource-load, timeline, action and evidence
  views. Baselines, scenario feasibility and hypothetical outputs remain
  separate from DataPlatform Findings and history.
- **Run the lab** presents inspection, assessment and diagnosis as one active
  stage at a time. The first actionable stage opens automatically, while
  completed earlier stages remain directly selectable. The controls still
  launch the existing synchronous DataPlatform commands: client identity is
  supplied only when inspection begins, while downstream ownership is resolved
  from run or snapshot metadata.

The global Client and Observation selectors remain in the **Data scope**
section at the end of the sidebar, beneath the navigation.

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

To discard and rebuild only the fixed synthetic identities (`demo-ui` and the
legacy `demo-001` fixture), run:

```powershell
.venv\Scripts\python.exe -m services.demo --reset
```

The reset removes those client directories from DataPlatform's local raw,
processed, curated and metadata areas and from the configured SchedulePlatform
output root. It refuses scenario directories whose saved configuration belongs
to another client. Other client data is not touched. Because there is no legacy
production scenario data, V1.0 packages are reset rather than migrated.

CP-SAT is not selectable in the console yet. Its presence in the
SchedulePlatform Python package is insufficient: the integration gate requires
a published V1.1 backend selector, a public `generate --backend cp-sat` CLI
contract, and a JSON result schema containing solver identity, version,
settings and authoritative-validation provenance. Until all three contracts
exist, bounded deterministic generation remains the only execution backend.

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
