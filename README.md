# Aztec Monitor

Aztec Network validator monitor with automatic Telegram alerts and report generation.

## Installation on Linux

### 1. Clone repository
```bash
git clone https://github.com/cyberomanov/aztec-monitor.git
cd aztec-monitor
```

### 2. Install dependencies
```bash
pip3 install -r requirements.txt
```

## Configuration

### 1. Configuration
Copy the example YAML config and adjust it to your infrastructure:
```bash
cp user_data/config-example.yaml user_data/config.yaml
```

The configuration is split into two sections:

- `monitoring` &mdash; runtime behaviour:
  - `threads` &mdash; how many validators are processed in parallel.
  - `proxy` &mdash; optional mobile proxy credentials (scheme/login/password supported).
  - `requests` &mdash; HTTP timeout, retry count and delay between requests.
  - `api` &mdash; Dashtec API base URL and validator endpoint template.
  - `report` &mdash; path template for generated reports (supports `{timestamp}` placeholder).
  - `attestation_success_threshold` &mdash; minimal successful attestation percentage before an alert.
  - `accounts_file` &mdash; CSV file with validator list.
  - `cycle` &mdash; enable/disable loop mode, sleep duration between cycles and maximum cycles count.
- `telegram` &mdash; notification settings with optional `thread_id` for sending alerts into a specific forum topic.

### 2. Validator list
Edit `user_data/accounts.csv`:
```csv
id,address,ip,port,note
1,0xAAAAAA,1.2.3.4,1492,4-8-200-netherlands
2,0xBBBBBB,5.6.7.8,1492,16-64-2048-estonia
```

## Running

```bash
python3 main.py
```

## Core Algorithm

1. **Initialization**:
   - Configuration loading
   - Reading validator list from CSV
   - Creating HTTP clients with proxy if configured

2. **Monitoring cycle** (for each validator):
   
   **2.1 Node availability check**:
   ```python
   # RPC request node_getL2Tips to the server where validator is installed
   POST http://{validator_ip}:{port}
   payload: {"jsonrpc": "2.0", "method": "node_getL2Tips", "params": [], "id": 67}
   ```
   
   **2.2 Synchronization check**:
   ```python
   # Get block height from explorer
   GET https://api.testnet.aztecscan.xyz/v1/temporary-api-key/l2/ui/blocks-for-table
   
   # Comparison: if node is behind by >3 blocks → alert
   if validator_height + 3 < explorer_height:
       send_telegram_alert()
   ```
   
   **2.3 Validator statistics collection**:
   ```python
   # Get data from Dashtec
   GET https://dashtec.xyz/api/validators/{validator_address}
   
   # Parsing: balance, rewards, attestations, blocks
   ```
   **2.4 Queue and registration information collection**:
   ```python
   # Get data from Dashtec
   GET https://dashtec.xyz/api/validators/queue?page=1&limit=10&search={validator_address}
   
   # Parsing: queue, whether validator is registered
   ```
   
   **2.5 Alert generation**:
   - RPC unavailability
   - Network desynchronization

3. **Data saving**:
   - CSV reports with timestamp in `user_data/reports/`
   - Logs of all operations via loguru

4. **Delays and retries**:
   - Between HTTP requests: `monitoring.requests.delay_between_requests`
   - Between cycles: `monitoring.cycle.sleep_minutes`
   - Retry on HTTP errors: `monitoring.requests.retries`

## Core Components

- **AztecBrowser**: HTTP client for API interaction
- **Telegram**: Sending alerts to Telegram
- **Balance**: Converting wei → STK (division by 10^18)
- **Retrier**: Decorator for retry attempts on errors
- **CsvAccount**: Validator data structure

## Monitored Metrics

- Validator status (validating/queue/registered)
- Synchronization height
- Balance and unclaimed rewards
- Attestation statistics (missed/successful)
- Block statistics (missed/mined/proposed)

Alerts are sent on critical events: node unavailability or desynchronization.
