import json
import os
from enum import Enum

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

API_KEY = os.environ.get("CLOCKIFY_API_KEY")

TIME_ENTRY_URL = "/workspaces/{workspaceId}/time-entries"
BASE_URL = "https://api.clockify.me/api/v1/"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}
ZEN_WORKSPACE_ID = os.environ["ZEN_WORKSPACE_ID"]


class ClockifyTimeEntry(BaseModel):
    start: str
    end: str
    billable: bool
    projectId: str


class ClientName(Enum):
    """Client names from Clockify"""

    stefan = "Stefan"
    fillip = "Filip and Pavel"
    traverse = "No Client"


class ClockifyProjectName(Enum):
    traverse = "tambo and traverseai"


class SlackProjectName(Enum):
    traverse = "traverseai-and-crm"


class ClockifyManager:
    def get_my_workspaces(self):
        with httpx.Client(base_url=BASE_URL, headers=HEADERS) as client:
            resp = client.get("workspaces")
        return resp.json()

    def get_all_projects_in_workspace(self, workspace_id: str):
        with httpx.Client(base_url=BASE_URL, headers=HEADERS) as client:
            resp = client.get(f"workspaces/{workspace_id}/projects")
        return resp.json()

    def get_my_active_workspaces(self):
        all_projects: list[dict] = self.get_all_projects_in_workspace(ZEN_WORKSPACE_ID)
        projects_map = {}  # key = customer, value = projectId
        for project in all_projects:
            if project["clientName"] == ClientName.stefan.value:
                projects_map["Stefan"] = project["id"]
            if project["clientName"] == ClientName.fillip.value:
                projects_map["Filip and Pavel"] = project["id"]
            if project["name"] == ClockifyProjectName.traverse.value:
                projects_map[ClockifyProjectName.traverse.value] = project["id"]

        return projects_map

    def add_time_entry(self, workspace_id: str, time_entry_data: ClockifyTimeEntry):
        with httpx.Client(base_url=BASE_URL, headers=HEADERS) as client:
            resp = client.post(
                f"workspaces/{workspace_id}/time-entries", data=time_entry_data.json()
            )
            print(resp.status_code, json.dumps(json.loads(resp.text), indent=4))
