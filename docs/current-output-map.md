# Current output map

This initial map is based on the DataPlatform metadata architecture. It should
be verified against one complete run and one failed run before deeper UI work.

Prototype 1 is local-only. Every source below is resolved beneath the local
directory configured by `DATALAB_PLATFORM_PATH`; cloud/object-storage paths
are intentionally not considered.

| Interface information | Current source | UI handling |
| --- | --- | --- |
| Run ID and overall state | `run.json` | Normalised by `services/run_reader.py` |
| Stage statuses and timestamps | `run.json` | Normalised by `services/run_reader.py` |
| Received sources | `sources.json` | Read by `services/discovery_reader.py` |
| Profiling summary | `profiling.json` | Read by `services/profiling_reader.py` |
| Field profiles | `profiles/<dataset>.json` | Reader expansion required |
| Processing result | `processing.json` | Reader expansion required |
| Validation status and findings | `validation.json` | Read by `services/validation_reader.py` |
| Example failing records | `validation_errors.csv` when present | Reader expansion required |
| Curated output evidence | `curation/*.json` | Reader expansion required |
| Dataset lineage and row counts | `metadata/snapshots/<dataset>/<run_id>.json` | Reader expansion required |

## Known platform-layout detail

The current repository places local evidence below
`local-data/metadata/runs`. The UI also supports `metadata/runs`, preserving the
portable contract proposed for the prototype.

## Next mapping pass

Catalogue the exact keys and types from:

- one successful run with curation evidence;
- one validation-failed or incomplete run;
- each dataset profile;
- `validation_errors.csv`, when present.

Then replace the temporary raw-JSON presentation in the detailed pages with
stable models and client-friendly components.
