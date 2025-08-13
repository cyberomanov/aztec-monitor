# Aztec Monitor

Монитор валидаторов Aztec Network с автоматическими алертами в Telegram и генерацией отчетов.

## Установка

### 1. Установка uv
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Установка зависимостей
```bash
uv sync
```

## Настройка

### 1. Конфигурация
Скопируйте пример конфига и настройте:
```bash
cp user_data/config-example.py user_data/config.py
```

Отредактируйте `user_data/config.py`:
```python
# Максимальное количество попыток при ошибках
max_retries = 3

# Мобильный прокси (опционально)
mobile_proxy = "socks5://user:pass@ip:port"  # или None

# Задержки между запросами (сек)
sleep_between_accs = (3, 5)      # между аккаунтами
sleep_between_loop = (600, 800)  # между циклами

# Telegram бот для алертов
bot_api_key = "YOUR_BOT_TOKEN"
alarm_chat_id = "YOUR_CHAT_ID"
```

### 2. Список валидаторов
Отредактируйте `user_data/accounts.csv`:
```csv
id,address,ip,port,note
1,0x1xxxxxx130,91.11.11.108,1492,my-validator-1
2,0x9xxxxxxFc4,91.12.12.107,1492,my-validator-2
```

## Запуск

```bash
uv run main.py
```

### Основной алгоритм

1. **Инициализация**:
   - Загрузка конфигурации
   - Чтение списка валидаторов из CSV
   - Создание HTTP клиентов с прокси

2. **Цикл мониторинга** (для каждого валидатора):
   
   **2.1 Проверка доступности ноды**:
   ```python
   # RPC запрос node_getL2Tips к валидатору
   POST http://{validator_ip}:{port}
   payload: {"jsonrpc": "2.0", "method": "node_getL2Tips", "params": [], "id": 67}
   ```
   
   **2.2 Проверка синхронизации**:
   ```python
   # Получение высоты блока с explorer
   GET https://api.testnet.aztecscan.xyz/v1/temporary-api-key/l2/ui/blocks-for-table
   
   # Сравнение: если нода отстает на >3 блока → алерт
   if validator_height + 3 < explorer_height:
       send_telegram_alert()
   ```
   
   **2.3 Сбор статистики валидатора**:
   ```python
   # Получение данных с Dashtec
   GET https://dashtec.xyz/api/validators/{validator_address}
   
   # Парсинг: баланс, награды, аттестации, блоки
   ```
   
   **2.4 Генерация алертов**:
   - Недоступность RPC
   - Рассинхронизация с сетью  
   - Статус "не найден" в dashtec

3. **Сохранение данных**:
   - CSV отчеты с timestamp в `user_data/reports/`
   - Логи всех операций через loguru

4. **Задержки и повторы**:
   - Между валидаторами: 3-5 сек
   - Между циклами: 10-13 мин
   - Retry при ошибках HTTP: до 3 попыток

### Основные компоненты

- **AztecBrowser**: HTTP клиент для взаимодействия с API
- **Telegram**: Отправка алертов в Telegram
- **Balance**: Конвертация wei → STK (деление на 10^18)
- **Retrier**: Decorator для повторных попыток при ошибках
- **CsvAccount**: Структура данных валидатора

### Мониторируемые метрики

- Статус валидатора (active/not_active)
- Высота синхронизации 
- Баланс и неполученные награды
- Статистика аттестаций (пропущено/успешно)
- Статистика блоков (пропущено/добыто/предложено)

Алерты отправляются при критических событиях: недоступность ноды, рассинхронизация, смена статуса валидатора.
