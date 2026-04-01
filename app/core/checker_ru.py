import json
from dataclasses import dataclass
from typing import Any

import asyncssh


@dataclass(frozen=True)
class RuCheckResult:
    slot: int
    alive: bool
    error: str | None = None


async def check_from_ru(
    *,
    vps2_host: str,
    vps2_user: str,
    ssh_key_path: str | None,
    items: list[dict[str, Any]],
    remote_checker_path: str = "/home/checker/checker.py",
    connect_timeout_s: float = 15.0,
) -> list[RuCheckResult]:
    payload = json.dumps(items, ensure_ascii=False)

    client_keys = None
    if ssh_key_path:
        client_keys = [ssh_key_path]

    async with asyncssh.connect(
        vps2_host,
        username=vps2_user,
        client_keys=client_keys,
        known_hosts=None,
        connect_timeout=connect_timeout_s,
    ) as conn:
        res = await conn.run(f"python3 {remote_checker_path} '{payload}'", check=False)

    if res.exit_status != 0:
        raise RuntimeError(
            f"RU checker failed: exit={res.exit_status} stderr={res.stderr.strip()}"
        )

    parsed = json.loads(res.stdout)
    results = []
    for row in parsed.get("results", []):
        results.append(
            RuCheckResult(
                slot=int(row.get("slot") or 0),
                alive=bool(row.get("alive")),
                error=row.get("error"),
            )
        )
    return results

