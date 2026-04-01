import asyncio
import logging

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers import build_router
from config import Settings
from core.scheduler import run_hourly_check
from core.state import StateStore


async def _scheduled_check(settings: Settings, bot: Bot) -> None:
    state = StateStore(settings.state_path)
    summary = await run_hourly_check(
        state=state,
        vps1_public_ip=settings.vps1_public_ip,
        vps2_host=settings.vps2_host,
        vps2_user=settings.vps2_user,
        vps2_ssh_key_path=settings.vps2_ssh_key_path,
        vps2_remote_checker_path=settings.vps2_remote_checker_path,
        configs_dir=settings.configs_dir,
    )
    if summary.regenerated:
        slots = sorted(state.load(), key=lambda s: s.slot)
        regenerated = ", ".join(str(x) for x in summary.regenerated)
        text = (
            f"Hourly check: перегенерированы слоты: {regenerated}\n\n"
            + "\n\n".join([f"{s.slot}) {s.link}" for s in slots])
        )
        await bot.send_message(settings.owner_chat_id, text)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(
        build_router(
            owner_chat_id=settings.owner_chat_id,
            state_path=settings.state_path,
            vps1_public_ip=settings.vps1_public_ip,
            vps2_host=settings.vps2_host,
            vps2_user=settings.vps2_user,
            vps2_ssh_key_path=settings.vps2_ssh_key_path,
            vps2_remote_checker_path=settings.vps2_remote_checker_path,
            configs_dir=settings.configs_dir,
        )
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_check,
        trigger="interval",
        hours=settings.check_interval_hours,
        args=[settings, bot],
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    # Trigger a startup check (non-blocking for bot)
    asyncio.create_task(_scheduled_check(settings, bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

