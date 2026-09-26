import subprocess
import platform
import hashlib

def get_machine_id() -> str:
    """Generates a stable machine fingerprint securely."""
    hw_id = ""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["wmic", "csproduct", "get", "uuid"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            hw_id = output.split('\n')[1].strip()
        elif platform.system() == "Darwin":
            output = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True)
            for line in output.split('\n'):
                if "IOPlatformUUID" in line:
                    hw_id = line.split('=')[1].strip().replace('"', '')
                    break
        else:
            with open('/etc/machine-id', 'r') as f:
                hw_id = f.read().strip()
    except Exception:
        import uuid
        hw_id = str(uuid.getnode())
        
    # Hash it so the raw UUID is never sent over the wire
    return hashlib.sha256(hw_id.encode()).hexdigest()