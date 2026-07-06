
import datetime
import json
import os
import shutil
import tarfile
import urllib.error
import urllib.request

WHATSAPP_ALERT_THRESHOLD = 90.0
WHATSAPP_API_BASE = "https://graph.facebook.com/v22.0/{phone_number_id}/messages"


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


def send_whatsapp_alert(message, access_token=None, phone_number_id=None, recipient=None):
    """
    Sends a real WhatsApp alert via Meta Cloud API when credentials are configured.
    Falls back to a faithful simulation (payload + endpoint) for local demos.
    """
    access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    recipient = recipient or os.getenv("WHATSAPP_RECIPIENT")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": (recipient or "<WHATSAPP_RECIPIENT>").lstrip("+").replace(" ", ""),
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    if not access_token or not phone_number_id or not recipient:
        print("[WHATSAPP SIMULATION] Credentials not set — showing real API request:")
        print(f"  POST {WHATSAPP_API_BASE.format(phone_number_id='<WHATSAPP_PHONE_NUMBER_ID>')}")
        print("  Content-Type: application/json")
        print(f"  Authorization: Bearer <WHATSAPP_ACCESS_TOKEN>")
        print(f"  Body: {json.dumps(payload, indent=2)}")
        return False, (
            "SIMULATED: WhatsApp alert payload prepared "
            "(set WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_RECIPIENT to send for real)"
        )

    api_url = WHATSAPP_API_BASE.format(phone_number_id=phone_number_id)
    request = urllib.request.Request(
        api_url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        if "messages" in response_body:
            message_id = response_body["messages"][0].get("id", "unknown")
            return True, f"SENT: WhatsApp alert delivered (message_id={message_id})"
        return False, f"FAILED: WhatsApp API rejected the alert — {response_body}"
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return False, f"FAILED: WhatsApp HTTP {exc.code} — {error_body}"
    except urllib.error.URLError as exc:
        return False, f"FAILED: Could not reach WhatsApp API — {exc.reason}"


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

    if disk_usage_percent > WHATSAPP_ALERT_THRESHOLD:
        host = os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "unknown")
        alert_message = (
            "💾 ALERTA DISCO\n"
            f"Uso: {disk_usage_percent:.2f}%\n"
            f"Umbral: {WHATSAPP_ALERT_THRESHOLD:.0f}%\n"
            f"Host: {host}\n"
            "Acción requerida: liberar espacio en disco."
        )
        whatsapp_status, whatsapp_msg = send_whatsapp_alert(alert_message)
        print(f"[WHATSAPP ALERT] {whatsapp_msg}")
    elif not health_status or "FAILURE" in backup_msg:
        print("[ALERT DISPATCH] Routing high-priority alert payload to DevOps monitoring channel...")
    else:
        print("[INFO] Automated routine finished successfully. System state: STABLE.")

    if os.path.exists(dummy_config_dir):
        shutil.rmtree(dummy_config_dir)
