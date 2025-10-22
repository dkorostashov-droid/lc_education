import os
import sys
import shutil
import asyncio
import signal

# ---------- диски та симлінки ----------
def ensure_disk_links():
    try:
        os.makedirs("/app/data/docs", exist_ok=True)
        os.makedirs("/app/data/store", exist_ok=True)

        def ensure_link(src: str, dst: str):
            # гарантуємо, що dst -> src (симлінк)
            if os.path.islink(dst):
                return
            if os.path.isdir(dst) and not os.path.islink(dst):
                shutil.rmtree(dst, ignore_errors=True)
            elif os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            os.symlink(src, dst, target_is_directory=True)

        ensure_link("/app/data/docs", "/app/docs")
        ensure_link("/app/data/store", "/app/store")
    except Exception as e:
        print(f"[warn] disk layout init: {e}", file=sys.stderr)

# ---------- запуск підпроцесів ----------
async def start(cmd, name):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

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

# ---------- main ----------
async def main():
    ensure_disk_links()

    port = int(os.environ.get("PORT", "8000"))
    print(f"[runner] launching api on port {port}", flush=True)

    # API
    _api = await start(
        ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", str(port)],
        "api",
    )

    # Бот з автоперезапуском
    async def run_bot_forever():
        backoff = 2
        while True:
            print("[runner] starting bot process", flush=True)
            bot = await start(["python", "bot_telegram.py"], "bot")
            rc = await bot.wait()
            print(f"[runner] bot exited with code {rc}", flush=True)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    bot_task = asyncio.create_task(run_bot_forever())

    # коректне завершення
    stop = asyncio.Event()

    def handle_sig(*_):
        stop.set()

    for s in (signal.SIGTERM, signal.SIGINT):
        try:
            asyncio.get_event_loop().add_signal_handler(s, handle_sig)
        except NotImplementedError:
            pass

    await stop.wait()

if __name__ == "__main__":
    asyncio.run(main())
