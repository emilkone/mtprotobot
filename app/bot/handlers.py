from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.scheduler import run_hourly_check
from core.state import StateStore


def build_router(
    *,
    owner_chat_id: int,
    state_path: str,
    vps1_public_ip: str,
    vps2_host: str,
    vps2_user: str,
    vps2_ssh_key_path: str | None,
    vps2_remote_checker_path: str,
    configs_dir: str,
) -> Router:
    router = Router()

    def is_owner(message: Message) -> bool:
        return bool(message.chat and message.chat.id == owner_chat_id)

    @router.message(Command("start"))
    async def start(m: Message) -> None:
        if not is_owner(m):
            return
        await m.answer(
            "Готово.\n\nКоманды:\n"
            "/proxies — показать текущие 5 прокси\n"
            "/status — краткий статус\n"
            "/check — проверить и при необходимости перегенерировать"
        )

    @router.message(Command("proxies"))
    async def proxies(m: Message) -> None:
        if not is_owner(m):
            return
        st = StateStore(state_path)
        slots = sorted(st.load(), key=lambda s: s.slot)
        if not slots:
            await m.answer("Пока нет состояния. Запусти `/check`.", parse_mode="Markdown")
            return
        text = "\n\n".join([f"{s.slot}) {s.link}" for s in slots])
        await m.answer(text)

    @router.message(Command("status"))
    async def status(m: Message) -> None:
        if not is_owner(m):
            return
        st = StateStore(state_path)
        slots = st.load()
        await m.answer(f"Слотов: {len(slots)}")

    @router.message(Command("check"))
    async def check(m: Message) -> None:
        if not is_owner(m):
            return
        await m.answer("Проверяю...")
        st = StateStore(state_path)
        summary = await run_hourly_check(
            state=st,
            vps1_public_ip=vps1_public_ip,
            vps2_host=vps2_host,
            vps2_user=vps2_user,
            vps2_ssh_key_path=vps2_ssh_key_path,
            vps2_remote_checker_path=vps2_remote_checker_path,
            configs_dir=configs_dir,
        )
        slots = sorted(st.load(), key=lambda s: s.slot)
        regenerated = (
            ", ".join(str(x) for x in summary.regenerated) if summary.regenerated else "нет"
        )
        text = (
            f"Готово.\n"
            f"alive(local)={summary.alive_local}/5, alive(ru)={summary.alive_ru}/5\n"
            f"перегенерированы слоты: {regenerated}\n\n"
            + "\n\n".join([f"{s.slot}) {s.link}" for s in slots])
        )
        await m.answer(text)

    return router

