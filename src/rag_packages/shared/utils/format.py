from datetime import datetime


def get_date_iso_str(date: datetime | str | None = None) -> str | None:
    if isinstance(date, datetime):
        return date.isoformat()
    elif isinstance(date, str):
        return date
    elif date is None:
        return None
    else:
        raise ValueError(f"Invalid type for date: {type(date)}")
