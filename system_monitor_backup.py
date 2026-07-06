
import datetime
import os
import shutil
import tarfile

from whatsapp_alerts import send_whatsapp_alert

WHATSAPP_ALERT_THRESHOLD = 90.0


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
        plant_name = os.environ.get("WHATSAPP_PLANT_NAME", "Servidor B-Intelligent")
        alert_detail = (
            f"Disco al {disk_usage_percent:.1f}% (umbral {WHATSAPP_ALERT_THRESHOLD:.0f}%) "
            f"en {host}. Liberar espacio."
        )
        whatsapp_status, whatsapp_msg = send_whatsapp_alert(alert_detail, plant_name=plant_name)
        print(f"[WHATSAPP ALERT] {whatsapp_msg}")
    elif not health_status or "FAILURE" in backup_msg:
        print("[ALERT DISPATCH] Routing high-priority alert payload to DevOps monitoring channel...")
    else:
        print("[INFO] Automated routine finished successfully. System state: STABLE.")

    if os.path.exists(dummy_config_dir):
        shutil.rmtree(dummy_config_dir)
