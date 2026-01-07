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
        color: #E0E0E0;
    }
    
    /* 背景色 */
    .stApp {
        background-color: #121212;
    }

    /* メインコンテナの余白調整 */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max_width: 700px;
    }

    /* タイトルスタイル */
    h1 {
        font-weight: 700 !important;
        color: #FFFFFF !important;
        text-align: center;
        margin-bottom: 2rem !important;
        background: -webkit-linear-gradient(45deg, #00C6FF, #0072FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    h2, h3 {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    /* Input Fields */
    .stTextInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
    }
    
    .stTextInput input:focus, .stDateInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: #0072FF !important;
        box-shadow: 0 0 0 1px #0072FF !important;
    }

    /* Button Style */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3.5rem;
        font-weight: 700;
        font-size: 1.1rem;
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
        border: none;
        color: white;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 114, 255, 0.3);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 114, 255, 0.4);
    }

    .stButton > button:active {
        transform: translateY(1px);
    }

    /* Card/Form Container */
    [data-testid="stForm"] {
        background-color: #1E1E1E;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #333333;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    /* Checkbox */
    .stCheckbox label {
        color: #B0B0B0 !important;
    }

    /* Notifications */
    .stAlert {
        border-radius: 10px;
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

# メインフォーム (Historyタブは削除済み)
# プロジェクトリストの取得
if is_connected:
    with st.spinner("Loading projects..."):
        projects = wrapper.get_projects()
    
    # 名前とIDの辞書を作成
    project_dict = {p["name"]: p["id"] for p in projects}
    project_names = ["(No Project)"] + list(project_dict.keys())
else:
    project_names = []
    project_dict = {}

# フォームエリア
with st.form("task_form", clear_on_submit=True):
    st.subheader("New Task")
    
    name = st.text_input("Task Name", placeholder="What gets done today?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        is_date_enabled = st.checkbox("Set Date", value=False)
        date = None
        if is_date_enabled:
            date = st.date_input("Date", datetime.now(), label_visibility="collapsed")
    
    with col2:
        selected_project_name = None
        if project_names:
            selected_project_name = st.selectbox("Project", project_names, label_visibility="collapsed")
        elif is_connected:
            st.caption("No projects found.")
    
    # スペースを空ける
    st.write("")
    
    submitted = st.form_submit_button("Save Task")
    
    if submitted:
        if not is_connected:
            st.error("Notionに接続できません。")
        elif not name:
            st.warning("タスク名を入力してください。")
        else:
            project_id = project_dict.get(selected_project_name)
            with st.spinner("Saving to Notion..."):
                success = wrapper.add_task(
                    name=name,
                    date=date,
                    project_id=project_id
                )
                if success:
                    st.success(f"Successfully added: **{name}**")
                else:
                    st.error("保存に失敗しました。ログを確認してください。")
