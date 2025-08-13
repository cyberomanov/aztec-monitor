# Aztec Monitor

Aztec Network validator monitor with automatic Telegram alerts and report generation.

## Installation on Linux

### 1. Clone repository
```bash
git clone https://github.com/cyberomanov/aztec-monitor.git
cd aztec-monitor
```

### 2. Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install dependencies
```bash
uv sync
```

## Configuration

### 1. Configuration
Copy the example config and configure:
```bash
cp user_data/config-example.py user_data/config.py
```

Edit `user_data/config.py`:
```python
# maximum number of retry attempts on errors
max_retries = 3

# mobile proxy for interaction with aztecscan and dashtec to avoid rate limits
# you can buy mobile/residential proxies here: https://proxyshard.com?ref=cyberomanov
# if you don't want to use proxy, you can leave this setting as is or fill with empty string
mobile_proxy = "socks5://log:pass@ip:port"
# mobile_proxy = "http://log:pass@ip:port"
# mobile_proxy = ""

# sleep in seconds between account checks
sleep_between_accs = (3, 5)
# sleep in seconds between cycles
sleep_between_loop = (600, 800)

# telegram bot API key
bot_api_key = "22222:AAA-BBB"
# chat ID where to send notifications for critical metrics
alarm_chat_id = "-1111"

```

### 2. Validator list
Edit `user_data/accounts.csv`:
```csv
id,address,ip,port,note
1,0xAAAAAA,1.2.3.4,1492,4-8-200-netherlands
2,0xBBBBBB,5.6.7.8,1492,16-64-2048-estonia
```

## Running

```bash
uv run main.py
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
   - Between validators: as configured, default: 3-5 sec
   - Between cycles: as configured, default: 10-13 min
   - Retry on HTTP errors: up to 3 attempts

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
