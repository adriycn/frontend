import re

def format_duration(seconds: int, force_hours: bool = False) -> str:
    if not seconds: return "00:00:00" if force_hours else "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0 or force_hours: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def parse_duration(time_str: str) -> int:
    parts = [int(p) if p.isdigit() else 0 for p in time_str.strip().split(":")]
    if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2: return parts[0] * 60 + parts[1]
    elif len(parts) == 1: return parts[0]
    return 0

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()