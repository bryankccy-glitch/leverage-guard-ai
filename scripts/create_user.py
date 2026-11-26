#!/usr/bin/env python3
"""建立 LeverageGuard 登入帳號（AUTH_MODE=supabase）。

帳號（例如 bryan）會建立成 Supabase Auth 的 bryan@leverageguard.local，登入頁只要輸入 bryan。
密碼與 service_role key 都在執行時由你自己輸入（不顯示、不寫入檔案或記錄）。
第一次登入時後端會自動建立 profile，角色是 investor（投資人）。

用法：python3 scripts/create_user.py
"""
from __future__ import annotations

import getpass
import json
import re
import sys
import urllib.error
import urllib.request

SUPABASE_URL = "https://cxkcomcsnrcgkmdecsml.supabase.co"
DOMAIN = "leverageguard.local"


def main() -> int:
    print("Supabase → Project Settings → API Keys 裡的 service_role（secret）key，貼上後按 Enter（不會顯示）")
    key = getpass.getpass("service_role key: ").strip()
    if not key:
        print("沒有輸入 key，結束。")
        return 1
    while True:
        name = input("\n帳號（例如 bryan；直接按 Enter 結束）: ").strip().lower()
        if not name:
            return 0
        if not re.fullmatch(r"[a-z0-9._-]{2,32}", name):
            print("帳號只能用英文小寫、數字和 . _ -，長度 2–32。")
            continue
        pw = getpass.getpass("密碼（不會顯示，至少 8 個字元）: ")
        if len(pw) < 8:
            print("密碼至少要 8 個字元。")
            continue
        if getpass.getpass("再輸入一次密碼: ") != pw:
            print("兩次密碼不一樣，請重來。")
            continue
        body = json.dumps({"email": f"{name}@{DOMAIN}", "password": pw, "email_confirm": True,
                           "user_metadata": {"display_name": name}}).encode()
        req = urllib.request.Request(f"{SUPABASE_URL}/auth/v1/admin/users", data=body, method="POST",
                                     headers={"apikey": key, "Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                uid = json.load(r).get("id", "")
            print(f"已建立帳號 {name}（{uid[:8]}…），登入頁輸入「{name}」和剛才的密碼即可。")
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            if "already" in msg.lower() or e.code == 422:
                print(f"帳號 {name} 已經存在，沒有變更。")
            else:
                print(f"建立失敗（HTTP {e.code}）。請確認 key 是 service_role。")
        finally:
            pw = ""


if __name__ == "__main__":
    sys.exit(main())
