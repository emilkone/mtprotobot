import secrets
import subprocess
from dataclasses import replace
from pathlib import Path

from .state import ProxySlot


def tls_domain_to_hex(tls_domain: str) -> str:
    return tls_domain.encode("ascii").hex()


def build_full_secret(tls_domain: str, secret32: str) -> str:
    # MTProxy "ee" / Fake-TLS: ee + 16-byte secret (32 hex) + ASCII domain in hex (see Telegram MTProxy docs)
    return f"ee{secret32}{tls_domain_to_hex(tls_domain)}"


def build_tg_link(host: str, port: int, tls_domain: str, secret32: str) -> str:
    return (
        f"https://t.me/proxy?server={host}&port={port}"
        f"&secret={build_full_secret(tls_domain, secret32)}"
    )


def gen_secret32() -> str:
    return secrets.token_hex(16)


def write_slot_secret_env(env_path: Path, tls_domain: str, secret32: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    secret = build_full_secret(tls_domain, secret32)
    env_path.write_text(f"SECRET={secret}\n", "utf-8")


def recreate_mtproto_container(
    slot: int,
    *,
    compose_file: str,
    compose_project_dir: str,
) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            compose_file,
            "--project-directory",
            compose_project_dir,
            "up",
            "-d",
            "--force-recreate",
            "--no-deps",
            f"mtproto_{slot}",
        ],
        check=True,
    )


def regenerate_slot(
    *,
    slot: ProxySlot,
    vps1_public_ip: str,
    mtproto_secrets_dir: str,
    compose_file: str,
    compose_project_dir: str,
) -> ProxySlot:
    new_secret32 = gen_secret32()
    env_path = Path(mtproto_secrets_dir) / f"slot_{slot.slot}.env"
    write_slot_secret_env(env_path, slot.tls_domain, new_secret32)
    recreate_mtproto_container(
        slot.slot,
        compose_file=compose_file,
        compose_project_dir=compose_project_dir,
    )
    new_link = build_tg_link(
        vps1_public_ip, slot.port, slot.tls_domain, new_secret32
    )
    return replace(slot, secret32=new_secret32, link=new_link)
