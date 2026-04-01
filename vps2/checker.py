#!/usr/bin/env python3
import json
import socket
import sys
import time
from typing import Any, Dict, List


def check_tcp(host: str, port: int, timeout_s: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(
            "Usage: checker.py '[{\"slot\":1,\"host\":\"1.2.3.4\",\"port\":443},...]'\n"
        )
        return 2

    try:
        payload = json.loads(sys.argv[1])
        if not isinstance(payload, list):
            raise ValueError("payload must be a list")
    except Exception as e:
        sys.stderr.write(f"Invalid JSON payload: {e}\n")
        return 2

    results: List[Dict[str, Any]] = []
    started = time.time()

    for item in payload:
        slot = item.get("slot")
        host = item.get("host")
        port = item.get("port")
        timeout_s = float(item.get("timeout_s", 5.0))

        alive = False
        err: str | None = None
        try:
            if not isinstance(host, str) or not isinstance(port, int):
                raise ValueError("host must be str and port must be int")
            alive = check_tcp(host, port, timeout_s=timeout_s)
        except Exception as e:
            alive = False
            err = str(e)

        row: Dict[str, Any] = {"slot": slot, "host": host, "port": port, "alive": alive}
        if err:
            row["error"] = err
        results.append(row)

    out = {
        "checked_at_unix": int(time.time()),
        "duration_ms": int((time.time() - started) * 1000),
        "results": results,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

