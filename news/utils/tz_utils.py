from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

DEFAULT_TIMEZONE = "America/Sao_Paulo"

def utc_to_local(dt_utc: datetime, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """Converte datetime UTC para timezone local."""
    return dt_utc.astimezone(ZoneInfo(tz_name))

def iso_to_local_str(iso_ts: str, tz_name: str = DEFAULT_TIMEZONE) -> Optional[str]:
    """Converte string ISO (em UTC) para string local formatada."""
    try:
        dt_utc = datetime.fromisoformat(iso_ts)
        dt_local = utc_to_local(dt_utc, tz_name)
        return dt_local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None
