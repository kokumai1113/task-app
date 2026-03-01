import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def wake_up():
    # ワークアウトアプリのURL
    url = "https://notion-workout-app.streamlit.app"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"アクセス開始: {url}")
        driver.get(url)
        
        # ボタンが現れるまで最大20秒待機
        wait = WebDriverWait(driver, 20)
        
        # 画像のテキスト「Yes, get this app back up!」に一致するボタンを探す
        xpath = "//button[contains(text(), 'Yes, get this app back up!')]"
        button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        
        button.click()
        print("✅ 'Wake Up' ボタンをクリックしました！起動を開始します。")
        
        # クリック後、起動処理が始まるのを少し待つ
        time.sleep(10)
        
    except Exception as e:
        # すでに起きている場合はボタンが見つからないので、こちらに飛びます
        print("通知: アプリは既に起きているか、ボタンが見つかりませんでした。")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    wake_up()