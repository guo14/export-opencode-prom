#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from prometheus_client import generate_latest, REGISTRY, Gauge

sys.stdout = sys.stderr = open(sys.stdout.fileno(), mode='w', buffering=1)

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "/data/opencode.db")
DEFAULT_PORT = 9092
DEFAULT_SCRAPE_INTERVAL = 15

sessions_total = Gauge("opencode_sessions_total", "Total number of sessions")
messages_total = Gauge("opencode_messages_total", "Total number of messages")
cost_total = Gauge("opencode_cost_total", "Total cost in USD")
tokens_input_total = Gauge("opencode_tokens_input_total", "Total input tokens")
tokens_output_total = Gauge("opencode_tokens_output_total", "Total output tokens")
tokens_reasoning_total = Gauge("opencode_tokens_reasoning_total", "Total reasoning tokens")
tokens_cache_read_total = Gauge("opencode_tokens_cache_read_total", "Total cache read tokens")
tokens_cache_write_total = Gauge("opencode_tokens_cache_write_total", "Total cache write tokens")
cost_per_day = Gauge("opencode_cost_per_day", "Average cost per day")
tokens_per_session = Gauge("opencode_tokens_per_session", "Average tokens per session")

model_messages = Gauge("opencode_model_messages_total", "Messages by model", ["model", "provider"])
model_cost = Gauge("opencode_model_cost_total", "Cost by model", ["model", "provider"])
model_tokens_input = Gauge("opencode_model_tokens_input_total", "Input tokens by model", ["model", "provider"])
model_tokens_output = Gauge("opencode_model_tokens_output_total", "Output tokens by model", ["model", "provider"])


def parse_message_data(data_json):
    try:
        data = json.loads(data_json) if isinstance(data_json, str) else data_json
    except (json.JSONDecodeError, TypeError):
        return None

    if data.get("role") != "assistant":
        return None

    tokens = data.get("tokens")
    if not tokens:
        return None

    return {
        "model_id": data.get("modelID"),
        "provider_id": data.get("providerID"),
        "agent": data.get("agent") or data.get("mode"),
        "cost": data.get("cost", 0) or 0,
        "tokens": {
            "input": max(0, tokens.get("input", 0) or 0),
            "output": max(0, tokens.get("output", 0) or 0),
            "reasoning": max(0, tokens.get("reasoning", 0) or 0),
            "cache_read": max(0, tokens.get("cache", {}).get("read", 0) or 0),
            "cache_write": max(0, tokens.get("cache", {}).get("write", 0) or 0),
        },
        "time_created": data.get("time", {}).get("created", 0),
    }


def collect_metrics(db_path):
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM session")
    sessions_count = cursor.fetchone()[0] or 0

    query = """
        SELECT m.id, m.session_id, m.data
        FROM message m
        WHERE json_extract(m.data, '$.role') = 'assistant'
          AND json_extract(m.data, '$.tokens') IS NOT NULL
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    messages_count = len(rows)

    total_cost = 0
    total_tokens = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    model_stats = {}

    earliest_time = None
    latest_time = None

    for row in rows:
        msg = parse_message_data(row[2])
        if not msg:
            continue

        total_cost += msg["cost"]
        for key in total_tokens:
            total_tokens[key] += msg["tokens"][key]

        if earliest_time is None or msg["time_created"] < earliest_time:
            earliest_time = msg["time_created"]
        if latest_time is None or msg["time_created"] > latest_time:
            latest_time = msg["time_created"]

        model_key = (msg["model_id"] or "unknown", msg["provider_id"] or "unknown")
        if model_key not in model_stats:
            model_stats[model_key] = {"messages": 0, "cost": 0, "tokens_input": 0, "tokens_output": 0}
        model_stats[model_key]["messages"] += 1
        model_stats[model_key]["cost"] += msg["cost"]
        model_stats[model_key]["tokens_input"] += msg["tokens"]["input"]
        model_stats[model_key]["tokens_output"] += msg["tokens"]["output"]

    conn.close()

    days = 1
    if earliest_time and latest_time:
        days = max(1, (latest_time - earliest_time) / (1000 * 3600 * 24))

    total_tokens_sum = sum(total_tokens.values())
    avg_tokens_per_session = total_tokens_sum / sessions_count if sessions_count > 0 else 0
    avg_cost_per_day = total_cost / days

    return {
        "sessions": sessions_count,
        "messages": messages_count,
        "cost": total_cost,
        "tokens": total_tokens,
        "cost_per_day": avg_cost_per_day,
        "tokens_per_session": avg_tokens_per_session,
        "model_stats": model_stats,
    }


def update_metrics(metrics):
    if metrics is None:
        return

    sessions_total.set(metrics["sessions"])
    messages_total.set(metrics["messages"])
    cost_total.set(metrics["cost"])
    tokens_input_total.set(metrics["tokens"]["input"])
    tokens_output_total.set(metrics["tokens"]["output"])
    tokens_reasoning_total.set(metrics["tokens"]["reasoning"])
    tokens_cache_read_total.set(metrics["tokens"]["cache_read"])
    tokens_cache_write_total.set(metrics["tokens"]["cache_write"])
    cost_per_day.set(metrics["cost_per_day"])
    tokens_per_session.set(metrics["tokens_per_session"])

    for (model, provider), stats in metrics["model_stats"].items():
        model_labels = {"model": model or "unknown", "provider": provider or "unknown"}
        model_messages.labels(**model_labels).set(stats["messages"])
        model_cost.labels(**model_labels).set(stats["cost"])
        model_tokens_input.labels(**model_labels).set(stats["tokens_input"])
        model_tokens_output.labels(**model_labels).set(stats["tokens_output"])


class PrometheusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"GET {self.path}", flush=True)
        if self.path == "/metrics" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_exporter(db_path, port, interval):
    print(f"Starting OpenCode exporter...", flush=True)
    print(f"Database: {db_path}", flush=True)
    print(f"Exists: {os.path.exists(db_path)}", flush=True)
    print(f"Port: {port}", flush=True)
    print(f"Scrape interval: {interval}s", flush=True)

    server = HTTPServer(("0.0.0.0", port), PrometheusHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Server running on http://0.0.0.0:{port}", flush=True)

    while True:
        try:
            metrics = collect_metrics(db_path)
            update_metrics(metrics)
            if metrics:
                print(f"Metrics: {metrics['sessions']} sessions, {metrics['messages']} messages, ${metrics['cost']:.4f}")
            else:
                print("No metrics collected (database not found or empty)")
        except Exception as e:
            print(f"Error collecting metrics: {e}")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="OpenCode Prometheus Exporter")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to OpenCode SQLite database")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to expose metrics")
    parser.add_argument("--interval", type=int, default=DEFAULT_SCRAPE_INTERVAL, help="Scrape interval in seconds")
    args = parser.parse_args()

    try:
        run_exporter(args.db_path, args.port, args.interval)
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
