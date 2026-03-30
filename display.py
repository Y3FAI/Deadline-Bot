from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import dateparser

RIYADH_TZ = ZoneInfo("Asia/Riyadh")
DATEPARSER_SETTINGS = {"TIMEZONE": "Asia/Riyadh", "RETURN_AS_TIMEZONE_AWARE": False}


def get_next_weekday_occurrence(dt):
    """Get the next occurrence of a weekday-based datetime."""
    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    target_weekday = dt.weekday()
    days_ahead = target_weekday - now.weekday()
    if days_ahead < 0:
        days_ahead += 7
    elif days_ahead == 0:
        target_time = dt.replace(year=now.year, month=now.month, day=now.day)
        if target_time <= now:
            days_ahead = 7
    next_date = now + timedelta(days=days_ahead)
    return next_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)


def get_effective_dates(start, due, recurring):
    """Get effective start/due dates, calculating next occurrence for recurring."""
    start_dt = dateparser.parse(start, settings=DATEPARSER_SETTINGS)
    due_dt = dateparser.parse(due, settings=DATEPARSER_SETTINGS)
    if recurring == "weekly":
        start_dt = get_next_weekday_occurrence(start_dt)
        due_dt = get_next_weekday_occurrence(due_dt)
    return start_dt, due_dt


def format_deadline(name, start_dt, due_dt, link, recurring):
    """Format a single deadline entry."""
    start_formatted = start_dt.strftime("%b %d, %I:%M %p")
    due_formatted = due_dt.strftime("%b %d, %I:%M %p")
    line = f"  📝 {name}"
    if recurring:
        line += " 🔁"
    line += f"\n  🟢 متاح: {start_formatted}\n  🔴 الموعد النهائي: {due_formatted}"
    if link:
        line += f"\n  🔗 {link}"
    return line


def format_deadline_with_id(id, name, start_dt, due_dt, link, recurring):
    """Format a deadline entry with ID prefix."""
    start_formatted = start_dt.strftime("%b %d, %I:%M %p")
    due_formatted = due_dt.strftime("%b %d, %I:%M %p")
    line = f"ID: {id}\n  📝 {name}"
    if recurring:
        line += " 🔁"
    line += f"\n  🟢 متاح: {start_formatted}\n  🔴 الموعد النهائي: {due_formatted}"
    if link:
        line += f"\n  🔗 {link}"
    return line


def format_grouped(deadlines):
    """Format deadlines grouped by class."""
    grouped = {}
    for id, name, class_name, start, due, link, recurring in deadlines:
        if class_name not in grouped:
            grouped[class_name] = []
        start_dt, due_dt = get_effective_dates(start, due, recurring)
        grouped[class_name].append((name, start_dt, due_dt, link, recurring))

    lines = []
    for class_name, items in grouped.items():
        lines.append(f"📚 {class_name}\n")
        for name, start_dt, due_dt, link, recurring in items:
            lines.append(format_deadline(name, start_dt, due_dt, link, recurring))
            lines.append("")
        lines.append("━━━━━━━━━━━━━━━\n")

    return "\n".join(lines[:-1]) if lines else ""


def format_with_ids(deadlines):
    """Format deadlines with IDs."""
    lines = ["المواعيد مع المعرّفات:\n"]
    for id, name, class_name, start, due, link, recurring in deadlines:
        start_dt, due_dt = get_effective_dates(start, due, recurring)
        lines.append(format_deadline_with_id(id, name, start_dt, due_dt, link, recurring))
        lines.append("")
    return "\n".join(lines)
