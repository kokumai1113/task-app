import os
from datetime import datetime
from notion_client import Client
import pandas as pd
import streamlit as st

class NotionWrapper:
    def __init__(self):
        # Streamlit secrets または環境変数から認証情報を取得
        # ローカル開発で .env を使う場合と Streamlit Cloud の Secrets を使う場合の両方に対応
        try:
            self.token = st.secrets["NOTION_TOKEN"]
            self.database_id = st.secrets["DATABASE_ID"]
        except (KeyError, FileNotFoundError):
            # st.secrets がない場合は環境変数を確認 (python-dotenvなどでロード済みを想定)
            self.token = os.getenv("NOTION_TOKEN")
            self.database_id = os.getenv("DATABASE_ID")

        if not self.token or not self.database_id:
            raise ValueError("Notion Token or Database ID is missing.")

        self.client = Client(auth=self.token)

    # 種目一覧DBのID (ハードコード)
    EXERCISE_DB_ID = "2c9998b2a5188049858fc05be5b60c99"

    def add_workout(self, exercise_id: str, weight: float, reps: int, sets: int, date: datetime.date = None):
        """
        新しいトレーニング記録をNotionに追加します。
        
        Args:
            exercise_id (str): 種目ページのID (Relation用)
            weight (float): 重量(kg)
            reps (int): 回数
            sets (int): セット数
            date (datetime.date, optional): 日付。指定がない場合は今日。
        """
        if date is None:
            date = datetime.now().date()
        
        date_iso = date.isoformat()

        # 名前は空欄で良いとのことですが、Notionの仕様上Titleは必須なので、
        # 日付などを入れておくのが無難ですが、空文字でも保存は可能です（タイトルなしページになる）。
        # ここでは日付を入れておきます。
        title_text = f"{date_iso} Workout"

        # プロパティの構築
        properties = {
            "名前": {
                "title": [
                    {
                        "text": {
                            "content": title_text
                        }
                    }
                ]
            },
            "日付": {
                "date": {
                    "start": date_iso
                }
            },
            "workout list": {
                "relation": [
                    {
                        "id": exercise_id
                    }
                ]
            },
            "重量 kg": {
                "number": weight
            },
            "reps": {
                "number": reps
            }
        }

        try:
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            return True
        except Exception as e:
            print(f"Error adding workout: {e}")
            return False

    def get_exercises(self):
        """
        種目一覧DBから種目を取得します。
        
        Returns:
            list: [{"id": page_id, "name": title}, ...]
        """
        try:
            response = self.client.databases.query(
                database_id=self.EXERCISE_DB_ID,
                sorts=[
                    {
                        "property": "名前", # 日本語環境のため "名前"
                        "direction": "ascending"
                    }
                ]
            )
            
            exercises = []
            for page in response["results"]:
                page_id = page["id"]
                props = page["properties"]
                # 日本語カラム名 "名前" を取得
                title_prop = props.get("名前")
                
                title_text = "Untitled"
                if title_prop and "title" in title_prop and title_prop["title"]:
                    title_text = title_prop["title"][0]["text"]["content"]
                
                exercises.append({"id": page_id, "name": title_text})
            
            return exercises

        except Exception as e:
            import notion_client
            st.error(f"Error fetching exercises: {e}. Make sure the integration is shared with the Exercise DB.")
            st.warning(f"Debug Info: notion-client version: {notion_client.__version__}")
            try:
                st.write(f"Databases attributes: {dir(self.client.databases)}")
            except Exception as debug_err:
                st.write(f"Could not inspect databases object: {debug_err}")
            return []

    def get_workouts(self, page_size: int = 20, exercise_map: dict = None):
        """
        過去のトレーニング記録を取得します。
        
        Args:
            page_size (int): 取得数
            exercise_map (dict): {exercise_id: exercise_name} のマッピング辞書。もし渡されればRelation IDを名前に変換します。

        Returns:
            pd.DataFrame: トレーニング履歴のデータフレーム
        """
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                page_size=page_size,
                sorts=[
                    {
                        "property": "日付",
                        "direction": "descending"
                    }
                ]
            )
            
            data = []
            for page in response["results"]:
                props = page["properties"]
                
                # 安全に値を取り出すためのヘルパー
                def get_title(prop):
                    res = prop.get("title", [])
                    return res[0]["text"]["content"] if res else ""
                
                def get_number(prop):
                    val = prop.get("number")
                    return val if val is not None else 0

                def get_date(prop):
                    res = prop.get("date", {})
                    return res.get("start") if res else ""
                
                def get_relation_name(prop):
                    # RelationプロパティからIDを取得
                    relation_list = prop.get("relation", [])
                    if not relation_list:
                        return "Unknown"
                    
                    ex_id = relation_list[0]["id"]
                    
                    if exercise_map and ex_id in exercise_map:
                        return exercise_map[ex_id]
                    return "Unknown"

                # データ抽出
                item = {
                    "Exercise": get_relation_name(props.get("workout list", {})),
                    "Date": get_date(props.get("日付", {})),
                    "Weight": get_number(props.get("重量 kg", {})),
                    "Reps": get_number(props.get("reps", {})),
                    "Sets": 0 
                }
                data.append(item)
            
            if not data:
                return pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps", "Sets"])

            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error fetching workouts: {e}")
            return pd.DataFrame()
