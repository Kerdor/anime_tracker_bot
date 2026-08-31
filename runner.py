from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_DIR / "main.py"
ALEMBIC_INI = PROJECT_DIR / "alembic.ini"
POLL_INTERVAL = 5


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return run_command("git", *args)


def get_head() -> str | None:
    result = run_git("rev-parse", "HEAD")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def pull() -> bool:
    result = run_git("pull")
    output = (result.stdout + result.stderr).strip()
    if output:
        print(f"[GIT] {output}", flush=True)
    return result.returncode == 0


def migrate() -> bool:
    print("[MIGRATION] Проверка и применение миграций Alembic...", flush=True)
    result = run_command("alembic", "-c", str(ALEMBIC_INI), "upgrade", "head")
    output = (result.stdout + result.stderr).strip()
    if output:
        print(f"[MIGRATION] {output}", flush=True)
    return result.returncode == 0


def start_bot() -> subprocess.Popen:
    print("[RUNNER] Запуск бота...", flush=True)
    return subprocess.Popen([sys.executable, str(MAIN_FILE)], cwd=PROJECT_DIR)


def stop_bot(process: subprocess.Popen) -> None:
    if process.poll() is None:
        print("[RUNNER] Останавливаем старый процесс бота...", flush=True)
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("[RUNNER] Бот не завершился вовремя, принудительно останавливаем.", flush=True)
            process.kill()
            process.wait()


def main() -> None:
    print(
        f"[RUNNER] Автообновление включено. Git проверяется каждые {POLL_INTERVAL} сек.",
        flush=True,
    )
    print("[RUNNER] Для остановки нажмите Ctrl+C.", flush=True)

    current_head = get_head()
    if current_head is None:
        print("[RUNNER] Не удалось определить текущий Git commit.", flush=True)
        return

    if not migrate():
        print("[MIGRATION] Ошибка миграции. Бот не запускается.", flush=True)
        return

    process = start_bot()

    try:
        while True:
            time.sleep(POLL_INTERVAL)

            if process.poll() is not None:
                print(f"[RUNNER] Бот завершился с кодом {process.returncode}.", flush=True)
                return

            old_head = current_head
            if not pull():
                print("[GIT] Pull не выполнен. Бот продолжает работать.", flush=True)
                continue

            new_head = get_head()
            if not new_head:
                print("[GIT] Не удалось определить новый commit. Бот продолжает работать.", flush=True)
                continue

            if new_head == old_head:
                current_head = new_head
                continue

            print(f"[RUNNER] Обнаружены изменения: {old_head} -> {new_head}", flush=True)
            stop_bot(process)

            if not migrate():
                print("[MIGRATION] Миграция не выполнена. Бот остаётся остановленным.", flush=True)
                return

            current_head = new_head
            process = start_bot()

    except KeyboardInterrupt:
        print("\n[RUNNER] Получен Ctrl+C.", flush=True)
        stop_bot(process)


if __name__ == "__main__":
    main()
