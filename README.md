# SGI Audit Dashboard

Interactive visualization dashboard for CONPREM GRAU's Integrated Management System (SGI) audit findings. Transforms a Markdown-formatted audit report into strategic decision-making tools covering ISO 9001:2015, ISO 14001:2015, and ISO 45001:2018.

## Features

- Executive summary with risk scores, compliance health, and finding counts
- Pareto analysis identifying the critical 80/20 distribution by process zone and ISO clause
- Risk heatmap showing risk intensity across process zones and standards
- SGI maturity radar chart benchmarking process performance
- Interactive findings table with search, sort, and drill-down
- Systemic transversal finding (HTS) dedicated panel
- Corrective action timeline with Gantt-style visualization
- CSV data export with filter metadata
- Dark mode interface with high-contrast vector charts

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Place your audit report Markdown file in `data/informe_hallazgos.md` (or specify a custom path), then run:

```bash
streamlit run src/app.py
```

To use a custom report file:

```bash
streamlit run src/app.py -- path/to/your/report.md
```

## Project Structure

```
├── src/
│   ├── app.py                  # Main Streamlit entry point
│   ├── parser.py               # Markdown report parser
│   ├── metrics.py              # Risk scoring and metrics engine
│   ├── pretty_printer.py       # DataFrame → Markdown serialization
│   ├── export.py               # CSV/image export module
│   ├── models.py               # Core data models (Finding, enums)
│   └── dashboard/
│       ├── filters.py          # Sidebar filters and apply logic
│       ├── executive_summary.py
│       ├── pareto.py           # Pareto chart visualizations
│       ├── heatmap.py          # Risk heatmap
│       ├── radar.py            # Maturity radar chart
│       ├── findings_table.py   # Interactive findings table
│       ├── hts_panel.py        # HTS systemic finding panel
│       └── timeline.py         # Corrective action timeline
├── tests/
│   ├── unit/
│   ├── property/
│   └── integration/
├── data/                       # Place audit report here
├── requirements.txt
├── pyproject.toml
└── .streamlit/config.toml      # Dark theme configuration
```

## Requirements

- Python 3.11+
- Streamlit ≥ 1.28
- Pandas ≥ 2.0
- Plotly ≥ 5.18

## Development

Install dev dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```
