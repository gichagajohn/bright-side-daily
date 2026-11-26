"""Timezone-aware due slots; delayed jobs keep their intended local date/time."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from bsd.common import config

def due(now=None):
    cfg=config(); local=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(cfg['timezone']))
    result=[]
    for slot in cfg['slots']:
        h,m=map(int,slot['time'].split(':'))
        intended=local.replace(hour=h,minute=m,second=0,microsecond=0)
        late=(local-intended).total_seconds()/60
        if 0 <= late < cfg['max_lateness_minutes']:
            result.append((slot, local.date().isoformat()))
    return result

def job_key(slot, day):
    return f"facebook:{day}:{slot['name']}:{slot['format']}"
