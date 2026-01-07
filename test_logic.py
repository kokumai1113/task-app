
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import date

# Mock streamlit before importing notion_wrapper
sys.modules["streamlit"] = MagicMock()
import streamlit as st
st.secrets = {"NOTION_TOKEN": "fake_token", "DATABASE_ID": "fake_db_id", "PROJECT_DB_ID": "fake_project_db_id"}

# Mock notion_client
sys.modules["notion_client"] = MagicMock()

# Now import the class to test
# We need to add the app directory to path
sys.path.append("/Users/isshin/apps/task app")
from notion_wrapper import NotionWrapper

class TestNotionWrapper(unittest.TestCase):
    def setUp(self):
        self.wrapper = NotionWrapper()
        # Mock fetch_db_schema to return known property names
        self.wrapper._fetch_db_schema = MagicMock(return_value={
            "title": "Task Name",
            "date": "Date",
            "relation": "Project"
        })
        self.wrapper.client = MagicMock()

    def test_add_task_no_date_no_project(self):
        self.wrapper.add_task("Test Task", date=None, project_id=None)
        
        # Verify creating page was called with correct properties
        args, kwargs = self.wrapper.client.pages.create.call_args
        properties = kwargs["properties"]
        
        self.assertIn("Task Name", properties)
        self.assertNotIn("Date", properties)
        self.assertNotIn("Project", properties)
        print("Test Task No Date No Project: Passed")

    def test_add_task_with_date_no_project(self):
        test_date = date(2023, 1, 1)
        self.wrapper.add_task("Test Task", date=test_date, project_id=None)
        
        args, kwargs = self.wrapper.client.pages.create.call_args
        properties = kwargs["properties"]
        
        self.assertIn("Date", properties)
        self.assertEqual(properties["Date"]["date"]["start"], "2023-01-01")
        self.assertNotIn("Project", properties)
        print("Test Task With Date No Project: Passed")

    def test_add_task_with_project_no_date(self):
        self.wrapper.add_task("Test Task", date=None, project_id="proj_123")
        
        args, kwargs = self.wrapper.client.pages.create.call_args
        properties = kwargs["properties"]
        
        self.assertIn("Project", properties)
        self.assertEqual(properties["Project"]["relation"][0]["id"], "proj_123")
        self.assertNotIn("Date", properties)
        print("Test Task With Project No Date: Passed")

if __name__ == '__main__':
    unittest.main()
