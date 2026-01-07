import os
from datetime import datetime
from notion_client import Client
import pandas as pd
import streamlit as st
import requests
import re # Added for _sanitize_id

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
        else:
            # IDのサニタイズ（URLがそのまま貼り付けられた場合などに対応）
            self.database_id = self._sanitize_id(self.database_id)
            self.project_db_id = self._sanitize_id(self.project_db_id)

        if self.token:
             self.client = Client(auth=self.token)

    def _sanitize_id(self, id_str):
        """
        NotionのIDを抽出・整形します。
        URLが渡された場合や、クエリパラメータがついている場合に対応します。
        """
        if not id_str:
            return None
        
        # 1. クエリパラメータを除去 (?v=...)
        id_str = id_str.split("?")[0]
        
        # 2. URLの場合、パスの最後を取得
        if "/" in id_str:
            id_str = id_str.split("/")[-1]

        # 3. "名前-ID" の形式の場合、末尾の32文字(または36文字)を抽出したいが、
        #    簡単な正規表現で 32文字のHEXを探す
        # 32文字のHEX (ハイフンなし)
        match = re.search(r'([a-f0-9]{32})', id_str)
        if match:
            return match.group(1)
        
        # UUID形式 (ハイフンあり)
        match_uuid = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', id_str)
        if match_uuid:
            return match_uuid.group(1)

        return id_str

    def _fetch_db_schema(self, database_id):
        """
        DBのスキーマ情報を取得し、プロパティ名（Date, Title, Relation）を特定します。
        Returns:
            dict: {"title": "Name", "date": "Date", "relation": "Project"} (defaults as fallback)
        """
        schema = {"title": "名前", "date": "日付", "relation": "Project"}
        
        # Requests fallback for robustness
        url = f"https://api.notion.com/v1/databases/{database_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                properties = data.get("properties", {})
                
                # Identify keys by type
                for name, prop in properties.items():
                    p_type = prop.get("type")
                    if p_type == "title":
                        schema["title"] = name
                    elif p_type == "date":
                        schema["date"] = name
                    elif p_type == "relation":
                        # Relation might be multiple, picking the first one found or matching "Project"
                        # If we have multiple relations, we might need better logic, but assuming one for now
                        # or prioritizing one named "Project" if exists.
                        if schema["relation"] == "Project" and name != "Project":
                            # If we haven't found "Project" yet, but found another relation, keep it as candidate
                            # But if we already have a default "Project", we only overwrite if we find "Project" (logic is tricky)
                            # Let's simple pick the *first* relation found if "Project" doesn't exist?
                            # Or better: Just check properties.
                            pass
                        
                        # Simplified logic: Update relation key if we find a relation property.
                        # We prioritize "Project" if it exists, otherwise use any relation.
                        if name == "Project" or schema["relation"] == "Project":
                             schema["relation"] = name
                        elif schema["relation"] != "Project":
                             # Already found a candidate, keep it? No, let's just create a list of relations if needed.
                             # For now, let's trust the default unless we find a relation.
                             schema["relation"] = name
                
                # If specifically found properties, update schema
                # Re-scan to be precise
                titles = [k for k, v in properties.items() if v["type"] == "title"]
                dates = [k for k, v in properties.items() if v["type"] == "date"]
                relations = [k for k, v in properties.items() if v["type"] == "relation"]
                
                if titles: schema["title"] = titles[0]
                if dates: schema["date"] = dates[0]
                # Try to fuzzy match "Project" or take first
                proj_rel = next((r for r in relations if "project" in r.lower()), None)
                if proj_rel:
                    schema["relation"] = proj_rel
                elif relations:
                    schema["relation"] = relations[0]
                    
            else:
                st.warning(f"Could not fetch DB schema (Status {response.status_code}). Using default property names.")
        except Exception as e:
            st.warning(f"Error determining DB schema: {e}")
            
        return schema

    def add_task(self, name: str, date: datetime.date, project_id: str):
        """
        新しいタスクをNotionに追加します。
        """
        # dateがNoneの場合は日付なしとして登録する
        
        # DBスキーマから正しいプロパティ名を取得
        schema = self._fetch_db_schema(self.database_id)
        prop_title = schema["title"]
        prop_date = schema["date"]
        prop_relation = schema["relation"]

        # プロパティの構築
        properties = {
            prop_title: {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },
            prop_relation: {
                "relation": [
                    {
                        "id": project_id
                    }
                ]
            }
        }
        
        # 日付がある場合のみプロパティに追加
        if date:
            date_iso = date.isoformat()
            properties[prop_date] = {
                "date": {
                    "start": date_iso
                }
            }

        try:
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            return True
        except Exception as e:
            st.error(f"Error adding task: {e}")
            return False

    def _query_database(self, database_id, sorts=None, page_size=100):
        """
        データベースクエリのラッパー。
        ライブラリのバージョンによって query メソッドがない場合のフォールバックを行います。
        直接 requests を使用して堅牢性を高めます。
        """
        body = {"page_size": page_size}
        if sorts:
            body["sorts"] = sorts

        # 1. 標準の client.databases.query を試す
        if hasattr(self.client.databases, "query"):
            return self.client.databases.query(
                database_id=database_id,
                **body
            )
        
        # 2. 直接APIを叩く (Requests Fallback)
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28", # 安定板を指定
            "Content-Type": "application/json"
        }
        
        # DEBUG: URLパスを確認
        # st.write(f"DEBUG: Requesting URL (Requests): '{url}'")

        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
        return response.json()

    def get_projects(self):
        """
        プロジェクトDBからプロジェクト一覧を取得します。
        
        Returns:
            list: [{"id": page_id, "name": title}, ...]
        """
        if not self.project_db_id:
            st.error("PROJECT_DB_ID is not set. Please check secrets.toml.")
            return []

        # DEBUG: IDの前後の空白などを確認
        # st.info(f"DEBUG: PROJECT_DB_ID = '{self.project_db_id}'")

        # 1. まず "名前" でのソートを試みる
        try:
            response = self._query_database(
                database_id=self.project_db_id,
                sorts=[{"property": "名前", "direction": "ascending"}]
            )
            return self._parse_projects(response, "名前")
        except Exception as e_name:
            # "名前" プロパティが存在しない可能性があるため、次は "Name" で試す
            try:
                response = self._query_database(
                    database_id=self.project_db_id,
                    sorts=[{"property": "Name", "direction": "ascending"}]
                )
                return self._parse_projects(response, "Name")
            except Exception as e_name_eng:
                # それでもダメならソートなしで取得
                try:
                    # st.warning(f"Sort failed ({e_name}, {e_name_eng}). Retrying without sort.")
                    response = self._query_database(
                        database_id=self.project_db_id
                    )
                    
                    if response["results"]:
                        # 最初のページのプロパティを表示してデバッグ支援
                        sample_props = response["results"][0]["properties"]
                        # DEBUG: st.info(f"Available properties: {list(sample_props.keys())}")
                        
                        # タイトルプロパティを探す
                        title_key = next((k for k, v in sample_props.items() if v["id"] == "title"), None) 
                        if not title_key:
                            title_key = next((k for k, v in sample_props.items() if v["type"] == "title"), "Name")
                        
                        return self._parse_projects(response, title_key)
                    else:
                        st.info("Project DB is empty.")
                        return []
                        
                except Exception as e_final:
                    st.error(f"Error fetching projects: {e_final}")
                    return []

    def _parse_projects(self, response, title_key):
        projects = []
        for page in response["results"]:
            page_id = page["id"]
            props = page["properties"]
            
            # タイトル取得
            title_prop = props.get(title_key)
            title_text = "Untitled"
            if title_prop and "title" in title_prop and title_prop["title"]:
                title_text = title_prop["title"][0]["text"]["content"]
            
            projects.append({"id": page_id, "name": title_text})
        
        return projects

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
            # DBスキーマから正しいプロパティ名を取得
            schema = self._fetch_db_schema(self.database_id)
            prop_title = schema["title"]
            prop_date = schema["date"]
            prop_relation = schema["relation"]

            response = self._query_database(
                database_id=self.database_id,
                page_size=page_size,
                sorts=[
                    {
                        "property": prop_date,
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
                item = {
                    "Task": get_title(props.get(prop_title, {})),
                    "Date": get_date(props.get(prop_date, {})),
                    "Project": get_relation_name(props.get(prop_relation, {}))
                }
                data.append(item)
            
            if not data:
                return pd.DataFrame(columns=["Date", "Task", "Project"])

            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return pd.DataFrame()
