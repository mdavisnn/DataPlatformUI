# Data Lab visual identity

The DataPlatformUI visual foundation uses native Streamlit theming and
components so that presentation remains portable and maintainable.

## Visual language

- Deep navy identifies the shared application shell and primary brand.
- Mint (`#5CC39D`) accents navigation, selection and primary actions.
- Dark teal provides accessible links and text accents on light surfaces.
- Red identifies high severity and blockers; amber identifies medium severity
  and caveats; cool grey identifies low severity; dark green identifies
  positive fitness status.
- Blue identifies neutral evidence and information.
- Violet is reserved for interpretation and hypotheses.
- White surfaces, cool-grey borders and an 8 px radius keep analytical
  content quiet and readable.
- A compact context strip above each hero anchors client, observation and
  snapshot identity without competing with page content.
- Page heroes use a one-word eyebrow followed by a question-led headline, for
  example `Overview: From evidence to better decisions`.

The source of truth for colours, typography, radii, chart palettes and
sidebar styling is `.streamlit/config.toml`. Do not create a second global
CSS theme.

## Shared presentation components

`components/console.py` owns the small native presentation primitives used
across pages:

- `render_hero` for page context and hierarchy;
- `render_metric_row` and `MetricCard` for responsive KPI cards;
- `render_panel` for bordered analytical sections;
- `render_observation_context` for visible client, observation and snapshot
  identity;
- finding and status helpers for deterministic diagnostic output;
- semantic severity and domain charts for optional Finding distributions.

These components receive already-calculated values. They must not calculate
fitness, diagnostic conditions or interpretations.

The core diagnostic experience follows a consistent review sequence:

1. orient to the selected client and canonical observation;
2. assess evidence and diagnostic coverage;
3. locate a deterministic Finding;
4. inspect its recorded rule context and evidence;
5. keep any later interpretation visibly separate.

Historical review applies the same hierarchy to a selected comparison or
trend window: scope and identity first, observed movement second, recorded
historical Findings third, and comparability or continuity caveats alongside
the evidence. Historical significance is never implied by visual emphasis.

Operational pages use bordered native panels, readiness badges and explicit
action labels to make the lifecycle legible. Only one lifecycle stage is open
at a time, and the first actionable stage opens automatically. Readiness is
descriptive only; every processing action still requires a user-controlled
command.

## Implementation rules

- Prefer native Streamlit containers, metrics, badges and Material Symbols.
- Keep global filters and application controls in the sidebar.
- Use sentence casing outside the Data Lab wordmark.
- Pair semantic colours with text or an icon.
- Keep brand mint for navigation and primary actions; reserve red, amber and
  grey for high, medium and low severity respectively.
- Keep executive defaults concise. Place distributions, technical detail and
  single-project inspection behind clearly labelled expanders when they are
  secondary to the main decision path.
- Preserve the distinction between `run_id`, `observation_date` and
  `snapshot_id`.
- Add page-specific CSS only when a native Streamlit element cannot express
  the required presentation.
