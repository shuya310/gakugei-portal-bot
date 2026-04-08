import asyncio
import os
import requests
from playwright.async_api import async_playwright

# ... 他のインポートはそのまま ...

# --- 設定（GitHubのSecretsから読み込む） ---
LOGIN_ID = os.getenv("PORTAL_USER")
PASSWORD = os.getenv("PORTAL_PASS")
TOPIC_NAME = os.getenv("NTFY_TOPIC")
# ---------------------------------------

# カテゴリごとの設定（表示名と、保存用ファイル名）
CHECK_LIST = [
    {"label": "個人宛お知らせ", "file": "last_personal.txt"},
    {"label": "お知らせ", "file": "last_general.txt"}
]

def send_notification(category, title):
    url = f"https://ntfy.sh/{TOPIC_NAME}"
    # メッセージ本体にカテゴリも含めてしまう
    message = f"【{category}】\n{title}"
    
    try:
        requests.post(url, 
            data=message.encode('utf-8'), # 本文はUTF-8で送るので日本語OK
            headers={
                "Title": "Gakugei Portal Update", # ここを英語に変更！
                "Priority": "high",
                "Tags": "bell"
            }
        )
        print(f"スマホに通知を飛ばしました: {category}")
    except Exception as e:
        print(f"通知失敗: {e}")

async def check_category(page, category_label, file_name):
    print(f"\n--- {category_label} をチェック中 ---")
    
    await page.get_by_role("combobox").first.select_option(label=category_label)
    await page.get_by_role("button", name="検索").click()
    
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)

    # ページ内の全てのタイトルを取得する
    all_titles = await page.locator(".link-txt.break").all_inner_texts()
    all_titles = [t.strip() for t in all_titles]

    if not all_titles:
        print(f"{category_label} に表示項目がありません。")
        return

    # 前回保存したタイトルを読み込む
    last_title = ""
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            last_title = f.read().strip()

    # 新着だけをリストにまとめる
    new_titles = []
    for t in all_titles:
        if t == last_title:
            # 前回と同じものが見つかったら、そこから下は既知のものなので終了
            break
        new_titles.append(t)

    if new_titles:
        print(f"★ {category_label} に {len(new_titles)}件 の新着あり！")
        # 古いものから順に通知を送るために逆順にする
        for t in reversed(new_titles):
            send_notification(category_label, t)
        
        # 一番新しい（リストの先頭）タイトルを保存する
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(all_titles[0])
    else:
        print("更新はありません。")

async def main():
    async with async_playwright() as p:
        # headless=True にすると、画面を表示せずに「頭脳」だけでブラウザを動かしてくれる
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("ログイン開始...")
        await page.goto("https://gportal.u-gakugei.ac.jp/portal/home/information/list")
        await page.fill('#floatingInput', LOGIN_ID)
        await page.fill('#floatingPassword', PASSWORD)
        await page.get_by_role("button", name="ログイン", exact=True).click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        # 順番にチェックを実行
        for item in CHECK_LIST:
            await check_category(page, item["label"], item["file"])

        print("\n全てのチェックが完了しました。")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
