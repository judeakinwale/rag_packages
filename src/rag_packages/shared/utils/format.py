from datetime import datetime


def get_date_iso_str(date: datetime | str) -> str:
    if isinstance(date, datetime):
        return date.isoformat()
    elif isinstance(date, str):
        return date
    else:
        raise ValueError(f"Invalid type for date: {type(date)}")
