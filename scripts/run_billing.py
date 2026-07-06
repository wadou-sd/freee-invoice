r"""締めバッチ実行。

使い方:
  python3 scripts/run_billing.py             # 当月分を下書き作成
  python3 scripts/run_billing.py 2026-07     # 月を指定
  python3 scripts/run_billing.py --dry-run   # 作成せずプレビュー
  python3 scripts/run_billing.py 2026-06 --dry-run

cron例（毎月末日 23:30 に当月分を下書き作成しログに追記）:
  30 23 28-31 * * [ "$(date +\%d -d tomorrow)" = "01" ] && \
    cd /root/projects/freee-invoice && /usr/bin/python3 scripts/run_billing.py \
    >> /root/projects/freee-invoice/billing.log 2>&1
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import billing  # noqa: E402


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if args:
        period = args[0]
    else:
        t = datetime.date.today()
        period = f"{t.year:04d}-{t.month:02d}"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 締めバッチ {period} {'(DRY-RUN)' if dry else ''} {ts} ===")
    billing.run(period, dry_run=dry)
    print("=== 終了 ===")


if __name__ == "__main__":
    main()
