import os
from datetime import datetime
from notion_client import Client
import pandas as pd
import streamlit as st

class NotionWrapper:
    def __init__(self):
        # Streamlit secrets または環境変数から認証情報を取得
        try:
            self.token = st.secrets["NOTION_TOKEN"]
            self.database_id = st.secrets["DATABASE_ID"] # Task DB ID
            self.project_db_id = st.secrets["PROJECT_DB_ID"] # Project DB ID
        except (KeyError, FileNotFoundError):
            # st.secrets がない場合は環境変数を確認
            self.token = os.getenv("NOTION_TOKEN")
            self.database_id = os.getenv("DATABASE_ID")
            self.project_db_id = os.getenv("PROJECT_DB_ID")

        if not self.token or not self.database_id or not self.project_db_id:
            # 開発中はまだPROJECT_DB_IDが設定されていないかもしれないので、Warningにとどめるか、あるいは必須とするか。
            # 今回は必須として扱うが、ユーザーに設定を促すメッセージはMain側で出す。
            pass

        if self.token:
             self.client = Client(auth=self.token)

    def add_task(self, name: str, date: datetime.date, project_id: str):
        """
        新しいタスクをNotionに追加します。
        
        Args:
            name (str): タスク名
            date (datetime.date): 実施予定日
            project_id (str): プロジェクトページのID (Relation用)
        """
        if date is None:
            date = datetime.now().date()
        
        date_iso = date.isoformat()

        # プロパティの構築
        properties = {
            "名前": {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },
            "日付": {
                "date": {
                    "start": date_iso
                }
            },
            "Project": { # Relation property name expected to be "Project" or check user env
                "relation": [
                    {
                        "id": project_id
                    }
                ]
            }
        }

        try:
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            return True
        except Exception as e:
            print(f"Error adding task: {e}")
            return False

    def get_projects(self):
        """
        プロジェクトDBからプロジェクト一覧を取得します。
        
        Returns:
            list: [{"id": page_id, "name": title}, ...]
        """
        try:
            response = self.client.databases.query(
                database_id=self.project_db_id,
                sorts=[
                    {
                        "property": "名前", 
                        "direction": "ascending"
                    }
                ]
            )
            
            projects = []
            for page in response["results"]:
                page_id = page["id"]
                props = page["properties"]
                
                # タイトル取得
                title_prop = props.get("名前")
                title_text = "Untitled"
                if title_prop and "title" in title_prop and title_prop["title"]:
                    title_text = title_prop["title"][0]["text"]["content"]
                
                projects.append({"id": page_id, "name": title_text})
            
            return projects

        except Exception as e:
            st.error(f"Error fetching projects: {e}. Check PROJECT_DB_ID.")
            return []

    def get_tasks(self, page_size: int = 20, project_map: dict = None):
        """
        タスク履歴を取得します。
        
        Args:
            page_size (int): 取得数
            project_map (dict): {project_id: project_name} のマッピング辞書。
        
        Returns:
            pd.DataFrame: タスク履歴のデータフレーム
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
                
                # Helper functions
                def get_title(prop):
                    res = prop.get("title", [])
                    return res[0]["text"]["content"] if res else ""
                
                def get_date(prop):
                    res = prop.get("date", {})
                    return res.get("start") if res else ""
                
                def get_relation_name(prop):
                    relation_list = prop.get("relation", [])
                    if not relation_list:
                        return "-"
                    
                    p_id = relation_list[0]["id"]
                    
                    if project_map and p_id in project_map:
                        return project_map[p_id]
                    return "Unknown Project"

                # データ抽出
                # Task DB properties assumption: "名前" (Title), "日付" (Date), "Project" (Relation)
                item = {
                    "Task": get_title(props.get("名前", {})),
                    "Date": get_date(props.get("日付", {})),
                    "Project": get_relation_name(props.get("Project", {}))
                }
                data.append(item)
            
            if not data:
                return pd.DataFrame(columns=["Date", "Task", "Project"])

            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return pd.DataFrame()
