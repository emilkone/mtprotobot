from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .checker import check_tcp
from .checker_ru import check_from_ru
from .proxy_manager import build_tg_link, regenerate_slot
from .state import ProxySlot, StateStore


@dataclass(frozen=True)
class CheckSummary:
    checked_at_unix: int
    alive_local: int
    alive_ru: int
    regenerated: list[int]


async def run_hourly_check(
    *,
    state: StateStore,
    vps1_public_ip: str,
    vps2_host: str,
    vps2_user: str,
    vps2_ssh_key_path: str | None,
    vps2_remote_checker_path: str = "/home/checker/checker.py",
    configs_dir: str,
    timeout_s: float = 5.0,
) -> CheckSummary:
    slots = state.load()
    if not slots:
        return CheckSummary(int(time.time()), 0, 0, [])

    # Ensure links are present (in case init.sh ran without VPS1_PUBLIC_IP).
    slots = [
        s
        if s.link
        else ProxySlot(
            slot=s.slot,
            port=s.port,
            secret32=s.secret32,
            tls_domain=s.tls_domain,
            link=build_tg_link(vps1_public_ip, s.port, s.tls_domain, s.secret32),
        )
        for s in slots
    ]

    # Local checks from VPS1.
    local_tasks = [
        check_tcp(vps1_public_ip, s.port, timeout_s=timeout_s) for s in slots
    ]
    local_res = await asyncio.gather(*local_tasks)
    local_alive = sum(1 for x in local_res if x)

    # RU checks from VPS2 (via SSH).
    ru_items = [{"slot": s.slot, "host": vps1_public_ip, "port": s.port} for s in slots]
    ru_res = await check_from_ru(
        vps2_host=vps2_host,
        vps2_user=vps2_user,
        ssh_key_path=vps2_ssh_key_path,
        items=ru_items,
        remote_checker_path=vps2_remote_checker_path,
    )
    ru_alive_by_slot = {r.slot: r.alive for r in ru_res}
    ru_alive = sum(1 for s in slots if ru_alive_by_slot.get(s.slot, False))

    regenerated: list[int] = []
    new_slots: list[ProxySlot] = []
    for idx, s in enumerate(slots):
        is_alive_local = bool(local_res[idx])
        is_alive_ru = bool(ru_alive_by_slot.get(s.slot, False))

        if is_alive_local and is_alive_ru:
            new_slots.append(s)
            continue

        new_s = regenerate_slot(
            slot=s, vps1_public_ip=vps1_public_ip, configs_dir=configs_dir
        )
        regenerated.append(s.slot)
        new_slots.append(new_s)

    state.save(new_slots)
    return CheckSummary(int(time.time()), local_alive, ru_alive, regenerated)

