# OpenCode Prometheus Exporter

A Prometheus exporter for [OpenCode](https://opencode.ai) that collects metrics from the OpenCode SQLite database and exposes them for Prometheus scraping.

## Features

- Collects session, message, token, and cost metrics
- Groups metrics by model and provider
- Exposes Prometheus-compatible `/metrics` endpoint
- Configurable scrape interval

## Requirements

- Docker
- Prometheus
- Grafana (optional, for visualization)
- OpenCode with SQLite database (OpenCode 1.2+)

## Quick Start

### 1. Build and Run

```bash
# Build and start the exporter
./start_opencode_exporter.sh
```

The exporter will:
- Build the Docker image
- Start the container as a daemon
- Mount your OpenCode database
- Expose metrics on port 9092

### 2. Configure Prometheus

Add to your `prometheus.yml`:

```yaml
- job_name: 'opencode'
  scrape_interval: 15s
  static_configs:
    - targets: ['localhost:9092']
```

### 3. Import Grafana Dashboard

Import `opencode_dashboard.json` into Grafana for pre-built visualizations.

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `opencode_sessions_total` | Gauge | Total number of sessions |
| `opencode_messages_total` | Gauge | Total number of messages |
| `opencode_cost_total` | Gauge | Total cost in USD |
| `opencode_tokens_input_total` | Gauge | Total input tokens |
| `opencode_tokens_output_total` | Gauge | Total output tokens |
| `opencode_tokens_reasoning_total` | Gauge | Total reasoning tokens |
| `opencode_tokens_cache_read_total` | Gauge | Total cache read tokens |
| `opencode_tokens_cache_write_total` | Gauge | Total cache write tokens |
| `opencode_cost_per_day` | Gauge | Average cost per day |
| `opencode_tokens_per_session` | Gauge | Average tokens per session |
| `opencode_model_messages_total` | Gauge | Messages by model/provider |
| `opencode_model_cost_total` | Gauge | Cost by model/provider |
| `opencode_model_tokens_input_total` | Gauge | Input tokens by model/provider |
| `opencode_model_tokens_output_total` | Gauge | Output tokens by model/provider |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/data/opencode.db` | Path to OpenCode SQLite database |

### Command Line Options

```bash
python exporter.py --db-path /path/to/opencode.db --port 9092 --interval 15
```

## Data Source

OpenCode stores data in `~/.local/share/opencode/opencode.db` (Linux/macOS).

The exporter mounts the host's home directory to access this database.

## Docker Details

- **Image**: `opencode-exporter`
- **Port**: 9092
- **Network**: Host mode (required for Prometheus to scrape)
- **Volume**: Mounts `$HOME` to access OpenCode database

## License

MIT
