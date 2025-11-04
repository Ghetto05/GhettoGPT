import requests
from requests.auth import HTTPBasicAuth

class AzureDevOpsClient:
    def __init__(self, org_url, project, pat):
        self.org_url = org_url.rstrip('/')
        self.project = project
        self.auth = HTTPBasicAuth('', pat)
        self.headers = {
            'Content-Type': 'application/json-patch+json'
        }

    def create_work_item(self, title, description):
        url = f"{self.org_url}/{self.project}/_apis/wit/workitems/$Issue?api-version=7.0"
        json_body = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            },
            {
                "op": "add",
                "path": "/fields/System.Description",
                "value": description
            },
            {
              "op": "add",
              "path": "/multilineFieldsFormat/System.Description",
              "value": "Markdown"
            }
        ]
        response = requests.post(url, auth=self.auth, headers=self.headers, json=json_body)
        response.raise_for_status()
        return response.json()

    def add_comment_to_work_item(self, work_item_id, comment):
        url = f"{self.org_url}/{self.project}/_apis/wit/workItems/{work_item_id}/comments?api-version=7.0-preview.3"
        json_body = {
            "text": comment
        }
        response = requests.post(url, auth=self.auth, headers={'Content-Type': 'application/json'}, json=json_body)
        response.raise_for_status()
        return response.json()

    def get_comments(self, work_item_id):
        url = f"{self.org_url}/{self.project}/_apis/wit/workItems/{work_item_id}/comments?api-version=7.0-preview.3"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()