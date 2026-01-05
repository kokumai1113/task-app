
from notion_client import Client

try:
    client = Client(auth="dummy")
    print("Type of client.databases:", type(client.databases))
    print("Attributes of client.databases:", dir(client.databases))
except Exception as e:
    print(f"Error during inspection: {e}")
