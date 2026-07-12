# scripts/manual_test.py
"""用真實 Google Sheet 測試解析與計算（不經過 LINE）。

事前準備：.env 中設定 GOOGLE_SERVICE_ACCOUNT_FILE（或 GOOGLE_SHEETS_API_KEY）。
用法：
  python scripts/manual_test.py                      # 互動模式
  python scripts/manual_test.py "50嵐 珍奶 微糖"      # 直接測一句（可多句）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import build_reply, init_services  # noqa: E402


def main():
    if not init_services():
        print("初始化失敗，請確認 .env 的 Google 金鑰設定")
        sys.exit(1)

    args = sys.argv[1:]
    if args:
        for text in args:
            print(f">>> {text}")
            print(build_reply(text))
            print()
        return

    print("互動模式（輸入 exit 離開）")
    while True:
        try:
            text = input("請輸入飲料資訊：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"exit", "quit"}:
            break
        if text:
            print(build_reply(text))


if __name__ == "__main__":
    main()
