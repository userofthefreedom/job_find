from __future__ import annotations
import sys

# Windows 콘솔/Task Scheduler 환경에서 UTF-8 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    print("준비 완료")


if __name__ == "__main__":
    main()
