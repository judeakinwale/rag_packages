from __future__ import annotations

import json
from typing import Any
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


def normalize_timestamp_to_seconds(ts: int) -> float:
    # 1_000_000_000_000 separates seconds from milliseconds
    seconds = ts / 1000.0 if ts >= 1_000_000_000_000 else float(ts)
    return seconds


def normalize_timestamp_to_milliseconds(ts: float | int) -> int:
    milliseconds = int(ts * 1000) if ts < 1_000_000_000_000 else int(ts)
    return milliseconds


def normalize_datetime_to_timestamp_ms(dt: datetime | int | str | None) -> int | None:
    if dt is None:
        return None

    if isinstance(dt, int):
        return normalize_timestamp_to_milliseconds(dt)

    if isinstance(dt, datetime):
        return int(dt.timestamp() * 1000)

    if isinstance(dt, str):
        date = datetime.fromisoformat(dt)
        return int(date.timestamp() * 1000)

    raise TypeError(
        f"Invalid timestamp type: {type(dt)}. Expected int, datetime, or str."
    )


def get_datetime_from_timestamp_ms(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None

    if isinstance(timestamp, float):
        timestamp = int(timestamp)

    if isinstance(timestamp, int):
        if len(str(timestamp)) == 10:
            timestamp = timestamp / 1000

        return datetime.fromtimestamp(timestamp)

    raise TypeError(f"Invalid timestamp type: {type(timestamp)}. Expected int.")


def extend_list_unique(
    target_list: list[Any] | None = None,
    extend_list: list[Any] | None = None,
    unique: bool = True,
) -> list[Any] | None:
    target_list = target_list.copy() if target_list is not None else None
    if target_list is None:
        list_copy = extend_list.copy() if extend_list is not None else None
        return list_copy

    if not extend_list:
        return target_list

    if unique:
        target_set = set(target_list)
        for item in extend_list:
            if item not in target_set:
                target_set.add(item)
                target_list.append(item)

        return target_list

    target_list.extend(extend_list)

    return target_list


def dicts_to_markdown(
    items: list[dict[str, Any]],
    fields: list[str],
    section_title: str,
    subtitle_key: str,
    *,
    field_labels: dict[str, str] | None = None,
    skip_empty: bool = True,
) -> str:
    """
    Convert a list of dictionaries into a markdown section.

    Parameters
    ----------
    items
        List of dictionaries to render.
    fields
        Keys to display under each item.
    section_title
        Level 3 markdown heading.
    subtitle_key
        Dictionary key whose value becomes the level 4 heading.
    field_labels
        Optional mapping of key -> display name.
    skip_empty
        If True, omit fields whose value is None or an empty string.
    """
    field_labels = field_labels or {}

    lines = [f"### {section_title}", ""]

    if not items:
        lines.append("_No items available._")
        return "\n".join(lines)

    for item in items:
        subtitle = item.get(subtitle_key, "Untitled")
        lines.append(f"#### {subtitle}")
        lines.append("")

        for field in fields:
            value = item.get(field, "not available")

            if skip_empty and (value is None or value == ""):
                continue

            label = field_labels.get(field, field.replace("_", " ").title())

            if isinstance(value, (dict, list)):
                lines.append(f"**{label}:**")
                lines.append("```json")
                lines.append(json.dumps(value, indent=2, ensure_ascii=False))
                lines.append("```")
            else:
                lines.append(f"- **{label}:** {value}")

        lines.append("")

    return "\n".join(lines)
