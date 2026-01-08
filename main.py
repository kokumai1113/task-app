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
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid #41424C;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .task-title {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 0.2rem;
    }

    .task-meta {
        color: #aaa;
        font-size: 0.9em;
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
    
    /* タブのスタイル調整（オプション） */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
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


# 共通データの読み込み (プロジェクト一覧)
project_dict = {}
project_names = []

if is_connected:
    with st.spinner("Loading projects..."):
        projects = wrapper.get_projects()
    
    # 名前とIDの辞書を作成 (ID -> Name for mapping, Name -> ID for selection)
    # Project selection uses Name -> ID
    # Task display uses ID -> Name
    project_dict_for_select = {p["name"]: p["id"] for p in projects} # Name -> ID
    project_map_for_display = {p["id"]: p["name"] for p in projects} # ID -> Name
    
    project_names = ["(No Project)"] + list(project_dict_for_select.keys())
else:
    project_dict_for_select = {}
    project_map_for_display = {}

# タブの作成
tab1, tab2 = st.tabs(["📝 Record", "📅 Daily Tasks"])

# --- Tab 1: Record (Add Task) ---
with tab1:
    st.header("Add New Task")
    
    is_date_enabled = st.checkbox("Set Date", value=False)

    with st.form("task_form", clear_on_submit=True):
        name = st.text_input("Task Name", placeholder="Enter task name...")
        
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
            else:
                project_id = project_dict_for_select.get(selected_project_name)
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

# --- Tab 2: Daily Tasks ---
with tab2:
    st.header("Daily Tasks")
    
    if not is_connected:
        st.error("Notion Connection Required")
    else:
        # Load tasks
        with st.spinner("Loading tasks..."):
            # Fetch a good number of tasks to ensure we cover recent ones
            # Pass project_map so it can resolve project IDs to names
            df = wrapper.get_tasks(page_size=100, project_map=project_map_for_display)


        if df.empty:
            st.info("No tasks found.")
        else:
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # Filter Logic
            # 1. Not Started (未着手) & Date == Today
            # 2. In Progress (進行中) (Any date)
            
            not_started_statuses = ["Not started", "Not Started", "未着手", "To Do", "To-do"]
            in_progress_statuses = ["In progress", "In Progress", "進行中", "Doing"]
            
            def is_target_task(row):
                status = str(row["Status"])
                date = str(row["Date"])
                
                is_not_started = status in not_started_statuses
                is_in_progress = status in in_progress_statuses
                is_today = date == today_str
                
                if is_not_started and is_today:
                    return True
                if is_in_progress:
                    return True
                return False

            # Apply filter
            target_tasks = df[df.apply(is_target_task, axis=1)]

            # Sort: In Progress first, then Not Started
            def sort_key(row):
                status = str(row["Status"])
                if status in in_progress_statuses:
                    return 0 # Top priority
                return 1

            if not target_tasks.empty:
                target_tasks["sort_key"] = target_tasks.apply(sort_key, axis=1)
                target_tasks = target_tasks.sort_values(by=["sort_key", "Date"])
                
                # Display tasks
                for index, row in target_tasks.iterrows():
                    # レイアウト: タスク名 (左) - ステータス (右)
                    c1, c2 = st.columns([0.7, 0.3])
                    
                    with c1:
                        # タスク名を大きく表示
                        st.markdown(f"##### {row['Task']}")
                        if row['Project'] != "-":
                            st.caption(f"📂 {row['Project']}")
                    
                    with c2:
                        # Status Updater
                        current_status = row['Status']
                        
                        # Dynamic options based on current status
                        options = [current_status] 
                        for s in ["未着手", "進行中", "完了"]:
                            if s not in options:
                                options.append(s)
                        
                        # Unique key for widgets in loop
                        new_status = st.selectbox(
                            "Status",
                            options=options,
                            index=0,
                            key=f"status_{row['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if new_status != current_status:
                            with st.spinner("Updating..."):
                                if wrapper.update_task_status(row['id'], new_status):
                                    st.success("Updated!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update.")
                    
                    st.divider()
            else:
                st.info("No tasks for today! 🎉")
