import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def wake_up():
    url = "https://task-app-wwjfcp2mkgxhv9xeezwns6.streamlit.app/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # webdriver-managerでChromeDriverを自動管理
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print(f"アクセス開始: {url}")
        driver.get(url)
        
        # ページロード待ち
        time.sleep(15)
        
        print(f"ページタイトル: {driver.title}")
        
        # Streamlitの公式 data-testid 属性でボタンを検索（最も安定）
        wait = WebDriverWait(driver, 30)
        
        try:
            button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="wakeup-button-viewer"]'))
            )
            print(f"✅ ウェイクアップボタン発見: '{button.text}'")
            button.click()
            print("✅ ボタンをクリックしました！")
            
            # 起動待ち
            time.sleep(20)
            print(f"起動後のタイトル: {driver.title}")
            print("✅ ウェイクアップ処理が完了しました！")
            
        except Exception:
            # ボタンが見つからない = アプリはすでに起動中
            print("ℹ️ ウェイクアップボタンが見つかりませんでした。")
            print("   → アプリは既に起動中です。")
            
    except Exception as e:
        print(f"エラー発生: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    wake_up()