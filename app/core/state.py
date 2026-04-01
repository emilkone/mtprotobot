import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ProxySlot:
    slot: int
    port: int
    secret32: str
    tls_domain: str
    link: str


def _normalize_slot(d: dict[str, Any]) -> ProxySlot:
    return ProxySlot(
        slot=int(d["slot"]),
        port=int(d["port"]),
        secret32=str(d["secret32"]),
        tls_domain=str(d["tls_domain"]),
        link=str(d.get("link", "")),
    )


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def load(self) -> list[ProxySlot]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text("utf-8"))
        if not isinstance(raw, list):
            raise ValueError("proxies.json must contain a list")
        return [_normalize_slot(x) for x in raw]

    def save(self, slots: Iterable[ProxySlot]) -> None:
        data = [asdict(s) for s in slots]
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
        tmp.replace(self.path)

