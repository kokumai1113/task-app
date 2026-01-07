import streamlit as st
import pandas as pd
from datetime import datetime
from notion_wrapper import NotionWrapper

# ページ設定
st.set_page_config(
    page_title="Task App",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# カスタムCSSの注入
def local_css():
    st.markdown("""
    <style>
    /* 全体のフォント設定 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    /* メインコンテナの余白調整（スマホ向け） */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* カード風デザインのコンテナクラス */
    .stCard {
        background-color: #262730;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border: 1px solid #41424C;
    }

    /* ボタンのスタイル */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        background-image: linear-gradient(to right, #00C6FF, #0072FF); /* Blue gradient */
        border: none; 
        color: white;
    }
    .stButton > button:hover {
        background-image: linear-gradient(to right, #00A6DF, #0052DF);
        border: none;
        color: white;
    }

    /* 入力フィールドのスタイル微調整 */
    .stTextInput, .stDateInput, .stSelectbox {
        margin-bottom: 0.5rem;
    }
    
    /* 履歴テーブルのヘッダー */
    th {
        color: #00C6FF !important;
    }

    </style>
    """, unsafe_allow_html=True)

local_css()

# タイトル
st.title("✅ Task App")

# Notionクライアントの初期化
try:
    wrapper = NotionWrapper()
    is_connected = True
except Exception as e:
    st.error("Notionとの連携設定が完了していません。secrets.tomlに `NOTION_TOKEN`, `DATABASE_ID`, `PROJECT_DB_ID` を設定してください。")
    st.warning(f"Error: {e}")
    is_connected = False

# タブの作成
tab1, tab2 = st.tabs(["📝 New Task", "📜 History"])

# --- タスク追加タブ ---
with tab1:
    st.header("Add New Task")
    
    # プロジェクトリストの取得
    if is_connected:
        with st.spinner("Loading projects..."):
            projects = wrapper.get_projects()
        
        # 名前とIDの辞書を作成
        project_dict = {p["name"]: p["id"] for p in projects}
        project_names = list(project_dict.keys())
    else:
        project_names = []
        project_dict = {}

    with st.form("task_form", clear_on_submit=True):
        name = st.text_input("Task Name", placeholder="Enter task name...")
        
        is_date_enabled = st.checkbox("Set Date", value=True)
        date = None
        if is_date_enabled:
            date = st.date_input("Date", datetime.now())
        
        selected_project_name = None
        if project_names:
            selected_project_name = st.selectbox("Project", project_names)
        elif is_connected:
            st.warning("No projects found. Please check PROJECT_DB_ID.")
        
        submitted = st.form_submit_button("Save Task")
        
        if submitted:
            if not is_connected:
                st.error("Notionに接続できません。")
            elif not name:
                st.warning("タスク名を入力してください。")
            elif not selected_project_name:
                st.warning("プロジェクトを選択してください。")
            else:
                project_id = project_dict[selected_project_name]
                with st.spinner("Saving to Notion..."):
                    success = wrapper.add_task(
                        name=name,
                        date=date,
                        project_id=project_id
                    )
                    if success:
                        st.success(f"Saved: {name} ({selected_project_name})")
                    else:
                        st.error("保存に失敗しました。ログを確認してください。")

# --- 履歴タブ ---
with tab2:
    st.header("History")
    
    if is_connected:
        with st.spinner("Loading history..."):
            try:
                # プロジェクト名解決のためのマップ作成
                # もし未取得なら取得する
                if 'projects' not in locals():
                     projects = wrapper.get_projects()
                     
                id_to_name_map = {p["id"]: p["name"] for p in projects}

                # 履歴取得
                df = wrapper.get_tasks(page_size=20, project_map=id_to_name_map)
                
                if not df.empty:
                    st.dataframe(
                        df,
                        column_config={
                            "Date": st.column_config.DateColumn("Date", format="MM/DD"),
                            "Task": "Task Name",
                            "Project": "Project",
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No tasks found yet.")
            except Exception as e:
                st.error(f"Error loading history: {e}")
    else:
        st.info("Please configure Notion credentials to see history.")
