from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Создаем экземпляр планировщика
scheduler = AsyncIOScheduler()

def add_cron_task(func, cron_string: str, args=None):
    """
    args: кортеж с аргументами, например (arg1, arg2)
    """
    trigger = CronTrigger.from_crontab(cron_string)

    scheduler.add_job(func, trigger, args=args)

async def start_scheduler():
    """Запуск планировщика"""
    scheduler.start()