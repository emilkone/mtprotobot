import asyncio


async def check_tcp(host: str, port: int, timeout_s: float = 5.0) -> bool:
    try:
        fut = asyncio.open_connection(host=host, port=port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout_s)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

