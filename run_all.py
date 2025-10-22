# run_all.py
import asyncio, os, signal, sys

PROCS = []

async def start(cmd, name):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    PROCS.append((name, proc))
    async def pipe(stream, writer):
        while True:
            line = await stream.readline()
            if not line:
                break
            writer.buffer.write(line)
            writer.flush()
    asyncio.create_task(pipe(proc.stdout, sys.stdout))
    asyncio.create_task(pipe(proc.stderr, sys.stderr))
    return proc

async def main():
    api = await start(
        ["python","-m","uvicorn","server:app","--host","0.0.0.0","--port","8000"],
        "api"
    )
    bot = await start(["python","bot_telegram.py"], "bot")

    # коректне завершення
    stop = asyncio.Event()
    def handle_sig(*_):
        stop.set()
    for s in (signal.SIGTERM, signal.SIGINT):
        try:
            asyncio.get_event_loop().add_signal_handler(s, handle_sig)
        except NotImplementedError:
            pass  # Windows

    await stop.wait()
    for name, p in PROCS:
        if p.returncode is None:
            p.terminate()
    await asyncio.gather(*[p.wait() for _, p in PROCS])

if __name__ == "__main__":
    asyncio.run(main())
