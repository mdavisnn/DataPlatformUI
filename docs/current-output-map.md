# Current output map

DataPlatformUI reads the client-owned local products below. Paths are resolved
beneath the storage root shared with DataPlatform.

| Interface information | Authoritative source | UI handling |
| --- | --- | --- |
| Client identity | `metadata/<client_id>/client.json` | Client selector and ownership validation |
| Run state and timestamps | `metadata/<client_id>/runs/<run_id>/run.json` | Run the lab |
| Run sources | `metadata/<client_id>/runs/<run_id>/sources.json` | Operational context |
| Canonical observation identity | `metadata/<client_id>/snapshots/<snapshot_id>/snapshot.json` | Shared observation context |
| Capability fitness and field-level condition evidence | `metadata/<client_id>/snapshots/<snapshot_id>/fitness.json` and its `evidence_object` | Evidence & fitness |
| Diagnostic execution and executive summary | `metadata/<client_id>/snapshots/<snapshot_id>/diagnosis.json` | Executive snapshot |
| Deterministic Findings | `metadata/<client_id>/snapshots/<snapshot_id>/findings.json` | Workspace, Findings and drill-down |
| Project comparison matrix | `curated/<client_id>/snapshots/<snapshot_id>/overview/project_health.csv` | Project health |
| Schedule project and activity products | Named `schedule` products in `diagnosis.json.diagnostics[].products` | Schedule |
| Resource, project, assignment-timeline, conflict and unassigned-work products | Named `resource` products in `diagnosis.json.diagnostics[].products` | Resources |
| Dependency edges, task connectivity and project coverage | Named `dependency` products in `diagnosis.json.diagnostics[].products` | Dependencies |
| Distribution observations, summaries and unusualness evidence | Named `exploratory` products in `diagnosis.json.diagnostics[].products` | Patterns |
| Canonical datasets | Objects referenced by `snapshot.json.datasets` | Plan on a page |
| Detailed diagnostic evidence | Objects referenced by Findings and diagnosis outcomes | Finding evidence |
| Historical comparison | `metadata/<client_id>/comparisons/<comparison_id>/comparison.json` | History |
| Historical trend | `metadata/<client_id>/trends/<trend_id>/trend.json` | History |
| Human interpretation | `metadata/<client_id>/interpretations/<interpretation_id>/session.json` | Interpretations |

The UI tolerates a missing optional analytical product and labels the
corresponding view as unavailable. It does not reinterpret missing output as a
healthy or empty result.

DataPlatform owns calculations, fitness classifications, diagnostic rules,
Finding creation and project-health statuses. The UI performs presentation-only
filtering, sorting and visualisation.
