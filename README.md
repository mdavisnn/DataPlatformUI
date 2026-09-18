# DataPlatformUI

DataPlatformUI is the local Streamlit interface for the DataPlatform PPM
diagnostic and historical analysis lab. It lets a consultant review governed
diagnostic products and, when deliberately selected, run DataPlatform's existing
deterministic inspect, assess, and diagnose commands.

The repositories remain separate:

- **DataPlatformUI** owns presentation, navigation, local product reading, and
  the guided command surface.
- **DataPlatform** owns source evidence, canonicalisation, fitness assessment,
  diagnostic rules, Findings, history, and interpretation records.

The UI does not calculate Findings, infer causes, or merge deterministic evidence
with consultant interpretation.

## Requirements

- A local checkout of DataPlatform.
- Python and `pip` available on the demonstration machine.
- DataPlatform evidence stored locally, either in the default `local-data`
  directory or a configured `DATA_PLATFORM_STORAGE_ROOT`.

Install the UI in its own virtual environment:

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

Set `DATALAB_PLATFORM_PATH` to the DataPlatform repository root:

```dotenv
DATALAB_PLATFORM_PATH=D:\Data Lab\DataPlatform
```

If DataPlatform uses storage outside `<DataPlatform>/local-data`, also set:

```dotenv
DATA_PLATFORM_STORAGE_ROOT=D:\path\to\diagnostic-data
```

Both locations must be accessible from the machine running Streamlit. `.env` and
`.streamlit/secrets.toml` are excluded from source control.

## Run the console

From the DataPlatformUI repository root:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit normally opens the console at `http://localhost:8501`.

## Console capabilities

### Review

- **Workspace** summarises the selected observation, dataset count, capability
  fitness, and priority Findings.
- **Evidence & fitness** keeps structural fitness, caveats, blockers, and
  unavailable rules separate from delivery Findings.
- **Findings** filters deterministic Findings and exposes their rule, affected
  entities, evidence, and governed supporting artifacts.
- **History** displays optional two-observation comparisons and multi-observation
  trend windows without making history a prerequisite for diagnosis.
- **Interpretations** displays recorded human interpretation sessions separately
  from deterministic products.

### Operate

**Run the lab** provides explicit controls for DataPlatform's existing
`lab.inspect`, `lab.assess`, and `lab.diagnose` modules. Commands run
synchronously with DataPlatform as the working directory and write to its
configured governed storage.

The UI does not silently weaken fitness controls. A not-fit capability can run
only when the consultant explicitly selects its capability-scoped override.

Use the operation page only with test evidence or evidence handled under the
appropriate client controls.

## Synthetic review data

To populate the console with a fixed synthetic observation:

```powershell
.venv\Scripts\python.exe -m services.demo
```

The command writes `demo-run-001` and `demo-2026-08-31` beneath the configured
storage root. Do not point it at a client evidence store.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The suite covers product discovery, governed artifact path safety, and headless
rendering of every console page.

## Prototype boundary

The console is local and consultant-facing. It does not provide authentication,
client segregation, cloud storage, background jobs, workflow orchestration, or
production deployment. Long-running operations remain visible in, and tied to,
the active Streamlit session.

See [USER_GUIDE.md](USER_GUIDE.md) for the operating walkthrough and
[docs/console.md](docs/console.md) for the release boundary.
