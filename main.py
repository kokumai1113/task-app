import streamlit as st
import pandas as pd
from datetime import datetime
from notion_wrapper import NotionWrapper
import sys
import subprocess
import notion_client

# Debug Info (Environment)
with st.expander("Debug Info (Environment)", expanded=True):
    st.write(f"Python version: {sys.version}")
    try:
        st.write(f"notion_client file: {notion_client.__file__}")
        st.write(f"notion_client version: {notion_client.__version__}")
    except AttributeError:
        st.error("Could not access notion_client attributes.")
    
    # Run pip list
    try:
        result = subprocess.run(["pip", "list"], capture_output=True, text=True)
        st.text("Pip list output:")
        st.code(result.stdout)
    except Exception as e:
        st.error(f"Pip list failed: {e}")

# ページ設定
st.set_page_config(
    page_title="Workout Tracker",
    page_icon="💪",
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
        background-image: linear-gradient(to right, #FF4B4B, #FF8F8F);
        border: none; 
        color: white;
    }
    .stButton > button:hover {
        background-image: linear-gradient(to right, #FF2B2B, #FF6F6F);
        border: none;
        color: white;
    }

    /* 入力フィールドのスタイル微調整 */
    .stNumberInput, .stTextInput, .stDateInput {
        margin-bottom: 0.5rem;
    }
    
    /* 履歴テーブルのヘッダー */
    th {
        color: #FF4B4B !important;
    }

    </style>
    """, unsafe_allow_html=True)

local_css()

# タイトル
st.title("💪 Workout Tracker")

# Notionクライアントの初期化
try:
    wrapper = NotionWrapper()
    is_connected = True
except Exception as e:
    st.error("Notionとの連携設定が完了していません。Secretsを設定してください。")
    st.warning(f"Error: {e}")
    is_connected = False

# タブの作成
tab1, tab2 = st.tabs(["📝 Record", "📜 History"])

# --- 記録タブ ---
with tab1:
    st.header("New Workout")
    
    # 種目リストの取得
    with st.spinner("Loading exercises..."):
        exercises = wrapper.get_exercises()
    
    # 名前とIDの辞書を作成
    exercise_dict = {e["name"]: e["id"] for e in exercises}
    exercise_names = list(exercise_dict.keys())

    with st.form("workout_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
        with col2:
            if exercise_names:
                selected_exercise_name = st.selectbox("Exercise", exercise_names)
            else:
                st.warning("No exercises found. Please check database connection.")
                selected_exercise_name = None
        
        col3, col4, col5 = st.columns(3)
        with col3:
            weight = st.number_input("Weight (kg)", min_value=0.0, step=2.5, format="%.1f")
        with col4:
            reps = st.number_input("Reps", min_value=0, step=1)
        with col5:
            sets = st.number_input("Sets", min_value=1, step=1, value=3)

        submitted = st.form_submit_button("Save Workout")
        
        if submitted:
            if not is_connected:
                st.error("Notionに接続できません。")
            elif not selected_exercise_name:
                st.warning("種目を選択してください。")
            else:
                exercise_id = exercise_dict[selected_exercise_name]
                with st.spinner("Saving to Notion..."):
                    success = wrapper.add_workout(
                        exercise_id=exercise_id,
                        weight=weight,
                        reps=reps,
                        sets=sets,
                        date=date
                    )
                    if success:
                        st.success(f"Saved: {selected_exercise_name} {weight}kg x {reps}reps")
                    else:
                        st.error("保存に失敗しました。ログを確認してください。")

# --- 履歴タブ ---
with tab2:
    st.header("History")
    if st.button("🔄 Refresh"):
        st.cache_data.clear() # データを再取得するためにキャッシュクリア（簡易的）

    if is_connected:
        with st.spinner("Loading history..."):
            df = wrapper.get_workouts(page_size=20)
            
            if not df.empty:
                # データフレームの表示などを調整
                # スマホで見やすいように、重要な列を左に、あるいはカード形式で表示など
                
                # スタイリングされたデータフレーム
                st.dataframe(
                    df,
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="MM/DD"),
                        "Exercise": "Exercise",
                        "Weight": st.column_config.NumberColumn("Kg", format="%.1f"),
                        "Reps": "Reps",
                        "Sets": "Sets",
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No workout history found yet.")
    else:
        st.info("Please configure Notion credentials to see history.")
