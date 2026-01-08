import streamlit as st
from notion_wrapper import NotionWrapper
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Daily Tasks", page_icon="📅")

st.title("📅 Daily Tasks")

# CSS for better styling
st.markdown("""
<style>
    .stCard {
        background-color: #262730;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid #41424C;
    }
    .task-title {
        font-weight: bold;
        font-size: 1.1em;
    }
    .task-meta {
        color: #aaa;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

try:
    wrapper = NotionWrapper()
except Exception as e:
    st.error(f"Error initializing Notion: {e}")
    st.stop()

# Load tasks
with st.spinner("Loading tasks..."):
    # Fetch a good number of tasks to ensure we cover recent ones
    df = wrapper.get_tasks(page_size=100)

if df.empty:
    st.info("No tasks found.")
else:
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Filter Logic
    # 1. Not Started (未着手) & Date == Today
    # 2. In Progress (進行中) (Any date)
    
    # "Not Started" patterns
    not_started_statuses = ["Not started", "Not Started", "未着手", "To Do", "To-do"]
    # "In Progress" patterns
    in_progress_statuses = ["In progress", "In Progress", "進行中", "Doing"]
    # "Done" patterns (for selection options)
    done_statuses = ["Done", "Completed", "完了", "Archived"]

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
    # Setting a sort key
    def sort_key(row):
        status = str(row["Status"])
        if status in in_progress_statuses:
            return 0 # Top priority
        return 1

    if not target_tasks.empty:
        target_tasks["sort_key"] = target_tasks.apply(sort_key, axis=1)
        target_tasks = target_tasks.sort_values(by=["sort_key", "Date"])
        
        st.write(f"Incomplete tasks for today: {len(target_tasks)}")
        
        # Display tasks
        for index, row in target_tasks.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="stCard">
                    <div class="task-title">{row['Task']}</div>
                    <div class="task-meta">📅 {row['Date']} | 📂 {row['Project']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Status Updater
                current_status = row['Status']
                
                # Dynamic options based on current status to ensure it's in the list
                options = [current_status] 
                # Add common options if not present
                for s in ["未着手", "進行中", "完了"]:
                    if s not in options:
                        options.append(s)
                
                new_status = st.selectbox(
                    "Status",
                    options=options,
                    index=0,
                    key=f"status_{row['id']}",
                    label_visibility="collapsed"
                )
                
                if new_status != current_status:
                    with st.spinner("Updating status..."):
                        if wrapper.update_task_status(row['id'], new_status):
                            st.success("Updated!")
                            st.rerun()
                        else:
                            st.error("Failed to update.")
                
                st.divider()
    else:
        st.info("No tasks for today! 🎉")
