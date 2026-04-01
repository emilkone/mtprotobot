import re
import secrets
from dataclasses import replace
from pathlib import Path

import docker

from .state import ProxySlot


def tls_domain_to_hex(tls_domain: str) -> str:
    return tls_domain.encode("ascii").hex()


def build_tg_link(host: str, port: int, tls_domain: str, secret32: str) -> str:
    return (
        f"https://t.me/proxy?server={host}&port={port}"
        f"&secret=ee{tls_domain_to_hex(tls_domain)}{secret32}"
    )


def gen_secret32() -> str:
    return secrets.token_hex(16)


def update_slot_config_secret(config_path: Path, slot: int, new_secret32: str) -> None:
    text = config_path.read_text("utf-8")
    # matches: slotN = "...."
    key = f"slot{slot}"
    pattern = rf'(^\s*{re.escape(key)}\s*=\s*\")([0-9a-fA-F]{{32}})(\"\s*$)'
    new_text, n = re.subn(pattern, rf"\g<1>{new_secret32}\g<3>", text, flags=re.M)
    if n != 1:
        raise RuntimeError(
            f"Expected to replace exactly 1 secret for {key} in {config_path}, replaced {n}"
        )
    config_path.write_text(new_text, "utf-8")


def restart_telemt_container(slot: int) -> None:
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    container = client.containers.get(f"telemt_{slot}")
    container.restart()


def regenerate_slot(
    *,
    slot: ProxySlot,
    vps1_public_ip: str,
    configs_dir: str,
) -> ProxySlot:
    new_secret32 = gen_secret32()
    config_path = Path(configs_dir) / f"config_{slot.slot}.toml"
    update_slot_config_secret(config_path, slot.slot, new_secret32)
    restart_telemt_container(slot.slot)
    new_link = build_tg_link(vps1_public_ip, slot.port, slot.tls_domain, new_secret32)
    return replace(slot, secret32=new_secret32, link=new_link)

