import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def wake_up():
    url = "https://notion-workout-app.streamlit.app"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 人間らしく見せるためのUser-Agent設定
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"アクセス開始: {url}")
        driver.get(url)
        
        # 画面がロードされるまで少し待つ
        time.sleep(10) 
        
        # ボタンをより広い条件で探す（テキストの一部が含まれていればOK）
        wait = WebDriverWait(driver, 30)
        xpath = "//button[contains(., 'get this app back up')]"
        
        button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        button.click()
        print("✅ 'Wake Up' ボタンを正常にクリックしました！")
        
        # 起動が始まるまで待機
        time.sleep(15)
        print("現在のページタイトル:", driver.title)
        
    except Exception as e:
        # デバッグ用に現在のページのソースを一部表示
        print("通知: ボタンが見つかりませんでした。既に起きている可能性があります。")
        # print(driver.page_source[:500]) # 必要ならコメントアウトを外して確認
    
    finally:
        driver.quit()

if __name__ == "__main__":
    wake_up()