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

# telegram notifications: True / False
enable_telegram_notifications = True
# telegram bot API key
bot_api_key = "22222:AAA-BBB"
# chat ID where to send notifications for critical metrics
alarm_chat_id = "-1111"

# minimum required attestation success rate (%).
# if the rate falls below this threshold, an alarm will be triggered.
attestation_success_threshold = 90
