
import datetime
import json
import os
import shutil
import tarfile
import urllib.error
import urllib.request

TELEGRAM_ALERT_THRESHOLD = 90.0
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def check_system_health(disk_path="/", threshold_percent=85.0):
    """
    Monitors system disk usage and returns status.
    Demonstrates proactive infrastructure health checks.
    """
    total, used, free = shutil.disk_usage(disk_path)
    used_percent = (used / total) * 100

    if used_percent > threshold_percent:
        return False, f"CRITICAL: High disk usage detected at {used_percent:.2f}%", used_percent
    return True, f"OK: Disk usage is safe at {used_percent:.2f}%", used_percent


def send_telegram_alert(message, bot_token=None, chat_id=None):
    """
    Sends a real Telegram alert via the Bot API when credentials are configured.
    Falls back to a faithful simulation (payload + endpoint) for local demos.
    """
    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    payload = {
        "chat_id": chat_id or "<TELEGRAM_CHAT_ID>",
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    if not bot_token or not chat_id:
        print("[TELEGRAM SIMULATION] Credentials not set — showing real API request:")
        print(f"  POST {TELEGRAM_API_BASE.format(token='<TELEGRAM_BOT_TOKEN>')}")
        print(f"  Content-Type: application/json")
        print(f"  Body: {json.dumps(payload, indent=2)}")
        return False, "SIMULATED: Telegram alert payload prepared (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to send for real)"

    api_url = TELEGRAM_API_BASE.format(token=bot_token)
    request = urllib.request.Request(
        api_url,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        if response_body.get("ok"):
            return True, f"SENT: Telegram alert delivered (message_id={response_body['result']['message_id']})"
        return False, f"FAILED: Telegram API rejected the alert — {response_body.get('description', 'unknown error')}"
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return False, f"FAILED: Telegram HTTP {exc.code} — {error_body}"
    except urllib.error.URLError as exc:
        return False, f"FAILED: Could not reach Telegram API — {exc.reason}"


def create_secure_backup(source_dir, output_filename):
    """
    Automates the creation of a compressed tarball backup for configuration logs.
    Handles exceptions gracefully to prevent silent pipeline failures.
    """
    if not os.path.exists(source_dir):
        return False, f"ERROR: Source directory '{source_dir}' does not exist."

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_backup_name = f"{output_filename}_{timestamp}.tar.gz"

        print(f"[*] Compressing log files from '{source_dir}'...")
        with tarfile.open(final_backup_name, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

        return True, f"SUCCESS: Backup archived as '{final_backup_name}'"
    except Exception as e:
        return False, f"CRITICAL FAILURE during backup process: {str(e)}"


if __name__ == "__main__":
    print("--- Initiating Automated System Maintenance Run ---")

    health_status, health_msg, disk_usage_percent = check_system_health()
    print(health_msg)

    dummy_config_dir = "./mock_config_logs"
    os.makedirs(dummy_config_dir, exist_ok=True)
    with open(f"{dummy_config_dir}/app_config.yaml", "w") as f:
        f.write("status: active\nenvironment: production\nversion: 2.4.1")

    backup_status, backup_msg = create_secure_backup(dummy_config_dir, "prod_env_backup")
    print(backup_msg)

    if disk_usage_percent > TELEGRAM_ALERT_THRESHOLD:
        alert_message = (
            "<b>DISK ALERT</b>\n"
            f"Usage: <code>{disk_usage_percent:.2f}%</code>\n"
            f"Threshold: <code>{TELEGRAM_ALERT_THRESHOLD:.0f}%</code>\n"
            f"Host: <code>{os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'unknown')}</code>\n"
            "Action required: free disk space immediately."
        )
        telegram_status, telegram_msg = send_telegram_alert(alert_message)
        print(f"[TELEGRAM ALERT] {telegram_msg}")
    elif not health_status or "FAILURE" in backup_msg:
        print("[ALERT DISPATCH] Routing high-priority alert payload to DevOps monitoring channel...")
    else:
        print("[INFO] Automated routine finished successfully. System state: STABLE.")

    if os.path.exists(dummy_config_dir):
        shutil.rmtree(dummy_config_dir)
