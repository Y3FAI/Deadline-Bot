import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update, Bot, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import init_db, add_deadline, get_all_deadlines, get_soon_deadlines, delete_deadline, get_all_holidays
from display import get_effective_dates, format_grouped, format_with_ids

RIYADH_TZ = ZoneInfo("Asia/Riyadh")
DATEPARSER_SETTINGS = {"TIMEZONE": "Asia/Riyadh", "RETURN_AS_TIMEZONE_AWARE": False}

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID") or 0) or None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! أنا بوت متابعة المواعيد النهائية.")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("فقط المشرف يمكنه إضافة مواعيد.")
        return

    text = update.message.text.replace("/add ", "")
    parts = [p.strip() for p in text.split("|")]

    if len(parts) < 4:
        await update.message.reply_text(
            "الصيغة: /add المادة | الاسم | البداية | الموعد | رابط (اختياري)"
        )
        return

    class_name = parts[0]
    name = parts[1]
    start = dateparser.parse(parts[2], settings=DATEPARSER_SETTINGS)
    due = dateparser.parse(parts[3], settings=DATEPARSER_SETTINGS)
    link = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
    recurring = parts[5].strip().lower() if len(parts) > 5 and parts[5].strip() else None

    if recurring and recurring != "weekly":
        await update.message.reply_text("فقط التكرار 'weekly' مدعوم.")
        return

    if not start:
        await update.message.reply_text("ما قدرت أفهم تاريخ البداية.")
        return

    if not due:
        await update.message.reply_text("ما قدرت أفهم الموعد النهائي.")
        return

    add_deadline(name, class_name, start, due, link, recurring)
    msg = f"تم ✓\n{class_name} — {name}\n🟢 {start.strftime('%b %d %I:%M %p')}\n🔴 {due.strftime('%b %d %I:%M %p')}"
    if recurring:
        msg += f"\n🔁 {recurring}"
    await update.message.reply_text(msg)


async def list_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadlines = get_all_deadlines()

    if not deadlines:
        await update.message.reply_text("مافيه مواعيد نهائية 🎉")
        return

    text = update.message.text.replace("/list", "").strip()
    is_owner = update.message.from_user.id == OWNER_ID

    if text:
        if text == "id" and is_owner:
            await update.message.reply_text(format_with_ids(deadlines))
            return

        deadlines = [d for d in deadlines if d[2].lower() == text.lower()]
        if not deadlines:
            await update.message.reply_text(f"مافيه مواعيد نهائية لـ {text}")
            return

    # Filter out past deadlines
    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    filtered = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if due_dt >= now:
            filtered.append(d)

    if not filtered:
        await update.message.reply_text("مافيه مواعيد نهائية 🎉")
        return

    await update.message.reply_text(format_grouped(filtered))


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadlines = get_soon_deadlines(days=1)

    if not deadlines:
        await update.message.reply_text("مافيه مواعيد نهائية اليوم 🎉")
        return

    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    filtered = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if due_dt.date() == now.date() and due_dt >= now:
            filtered.append(d)

    if not filtered:
        await update.message.reply_text("مافيه مواعيد نهائية اليوم 🎉")
        return

    await update.message.reply_text(format_grouped(filtered))


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadlines = get_soon_deadlines(days=30)

    if not deadlines:
        await update.message.reply_text("مافيه مواعيد نهائية هالشهر 🎉")
        return

    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    cutoff = now + timedelta(days=30)
    filtered = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if now <= due_dt <= cutoff:
            filtered.append(d)

    if not filtered:
        await update.message.reply_text("مافيه مواعيد نهائية هالشهر 🎉")
        return

    await update.message.reply_text(format_grouped(filtered))


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadlines = get_soon_deadlines(days=7)

    if not deadlines:
        await update.message.reply_text("مافيه مواعيد نهائية هالأسبوع 🎉")
        return

    # Filter recurring deadlines to only those due within 7 days
    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    cutoff = now + timedelta(days=7)
    filtered = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if now <= due_dt <= cutoff:
            filtered.append(d)

    if not filtered:
        await update.message.reply_text("مافيه مواعيد نهائية هالأسبوع 🎉")
        return

    await update.message.reply_text(format_grouped(filtered))


async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadlines = get_all_deadlines()

    if not deadlines:
        await update.message.reply_text("مافيه مواعيد نهائية 🎉")
        return

    # Sort by effective due date and take first 3
    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    sorted_deadlines = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if due_dt > now:
            sorted_deadlines.append((due_dt, d))

    sorted_deadlines.sort(key=lambda x: x[0])
    top_3 = [d for _, d in sorted_deadlines[:3]]

    if not top_3:
        await update.message.reply_text("مافيه مواعيد نهائية قادمة 🎉")
        return

    await update.message.reply_text("📌 مواعيد نهائية قادمة:\n\n" + format_grouped(top_3))


async def holidays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    holiday_list = get_all_holidays()

    if not holiday_list:
        await update.message.reply_text("ما في إجازات مضافة.")
        return

    lines = ["🗓 الإجازات\n"]
    for id, name, start_date, end_date in holiday_list:
        if end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            duration = (end - start).days + 1
            lines.append(f"• {name}\n  {start_date} → {end_date} ({duration} يوم)\n")
        else:
            lines.append(f"• {name}\n  {start_date}\n")

    await update.message.reply_text("\n".join(lines))


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("فقط المشرف يمكنه حذف المواعيد.")
        return

    text = update.message.text.replace("/delete", "").strip()

    if not text:
        await update.message.reply_text("الصيغة: /delete id\n\nاستخدم /list لعرض المعرّفات.")
        return

    try:
        id = int(text)
    except ValueError:
        await update.message.reply_text("المعرّف لازم يكون رقم.")
        return

    delete_deadline(id)
    await update.message.reply_text("تم الحذف ✓")


async def test_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a test notification to the group."""
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("فقط المشرف يمكنه اختبار الإشعارات.")
        return

    await context.bot.send_message(
        CHAT_ID,
        "🧪 إشعار تجريبي\n\nالبوت يعمل!",
        message_thread_id=TOPIC_ID
    )
    await update.message.reply_text("تم إرسال الإشعار التجريبي ✓")


async def check_reminders(bot: Bot):
    """Check for deadlines and send reminders."""
    deadlines = get_all_deadlines()
    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)

    for id, name, class_name, start, due, link, recurring in deadlines:
        _, due_dt = get_effective_dates(start, due, recurring)
        hours_until = (due_dt - now).total_seconds() / 3600

        # 24h reminder: due in 23-24 hours
        if 23 <= hours_until < 24:
            await bot.send_message(
                CHAT_ID,
                f"⏰ تذكير باقي ٢٤ ساعة على الموعد النهائي\n📚 {class_name} — {name}\n🔴 الموعد النهائي: {due_dt.strftime('%b %d, %I:%M %p')}",
                message_thread_id=TOPIC_ID
            )
        # 1h reminder: due in 1-2 hours
        elif 1 <= hours_until < 2:
            await bot.send_message(
                CHAT_ID,
                f"🚨 تذكير باقي ساعة على الموعد النهائي\n📚 {class_name} — {name}\n🔴 الموعد النهائي: {due_dt.strftime('%b %d, %I:%M %p')}",
                message_thread_id=TOPIC_ID
            )


async def weekly_summary(bot: Bot):
    """Send weekly summary of upcoming deadlines."""
    deadlines = get_soon_deadlines(days=7)

    if not deadlines:
        await bot.send_message(CHAT_ID, "📅 ملخص الأسبوع\n\nمافيه مواعيد نهائية هالأسبوع 🎉", message_thread_id=TOPIC_ID)
        return

    now = datetime.now(RIYADH_TZ).replace(tzinfo=None)
    cutoff = now + timedelta(days=7)
    filtered = []
    for d in deadlines:
        id, name, class_name, start, due, link, recurring = d
        _, due_dt = get_effective_dates(start, due, recurring)
        if now <= due_dt <= cutoff:
            filtered.append(d)

    if not filtered:
        await bot.send_message(CHAT_ID, "📅 ملخص الأسبوع\n\nمافيه مواعيد نهائية هالأسبوع 🎉", message_thread_id=TOPIC_ID)
        return

    msg = "📅 ملخص الأسبوع\n\n" + format_grouped(filtered)
    await bot.send_message(CHAT_ID, msg, message_thread_id=TOPIC_ID)


async def post_init(application):
    """Start scheduler and set bot commands."""
    await application.bot.set_my_commands([
        BotCommand("list", "جميع المواعيد"),
        BotCommand("today", "مواعيد اليوم"),
        BotCommand("week", "مواعيد الأسبوع"),
        BotCommand("month", "مواعيد الشهر"),
        BotCommand("upcoming", "أقرب ٣ مواعيد"),
        BotCommand("holidays", "الإجازات الأكاديمية"),
    ])

    scheduler = AsyncIOScheduler(timezone=RIYADH_TZ)
    scheduler.add_job(check_reminders, "interval", hours=1, args=[application.bot])
    scheduler.add_job(weekly_summary, "cron", day_of_week="sat", hour=17, args=[application.bot])
    scheduler.start()


def main():
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_deadlines))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CommandHandler("holidays", holidays))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("test", test_notify))

    app.run_polling()


if __name__ == "__main__":
    main()
