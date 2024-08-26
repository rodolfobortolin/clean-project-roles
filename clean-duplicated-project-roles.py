import json
import logging
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Constants
CLOUD_BASE_URL = "https://domain.atlassian.net"
CLOUD_EMAIL = "rodolfobortolin@gmail.com"
CLOUD_TOKEN = ""
AUTH = HTTPBasicAuth(CLOUD_EMAIL, CLOUD_TOKEN)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}
PROJECT_LIST = ['EFJ2K']  # Add project keys to this list to limit to specific projects, leave empty to process all
PERMISSION_SCHEME_LIST = [10000]  # Add permission scheme IDs to this list to limit to specific schemes, leave empty to process all

def clean_permission_schemes():
    permission_schemes = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/permissionscheme', headers=HEADERS, auth=AUTH).json()

    for index, scheme in enumerate(permission_schemes["permissionSchemes"], start=1):
        if PERMISSION_SCHEME_LIST and scheme["id"] not in PERMISSION_SCHEME_LIST:
            continue

        logging.info(f'> Permission Name: {scheme["name"]}')

        scheme_details = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/permissionscheme/{scheme["id"]}?expand=all', headers=HEADERS, auth=AUTH).json()
        permissions = scheme_details["permissions"]

        for permission in permissions:
            if "projectRole" in permission["holder"]["type"] and "(migrated)" in permission["holder"]["projectRole"]["name"]:
                normal_role_name = permission["holder"]["projectRole"]["name"].split(" (migrated)", 1)[0]
                project_roles = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/role', headers=HEADERS, auth=AUTH).json()

                for role in project_roles:
                    if role["name"] == normal_role_name:
                        payload = {
                            "holder": {
                                "type": "projectRole",
                                "value": role["id"]
                            },
                            "permission": permission["permission"]
                        }
                        requests.post(f'{CLOUD_BASE_URL}/rest/api/3/permissionscheme/{scheme["id"]}/permission', headers=HEADERS, data=json.dumps(payload), auth=AUTH)

def clean_projects():
    projects = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/project', headers=HEADERS, auth=AUTH).json()

    for index, project in enumerate(projects, start=1):
        if PROJECT_LIST and project["key"] not in PROJECT_LIST:
            continue
        
        logging.info(f'> Project Name: {project["name"]} ')

        if "classic" in project["style"]:
            project_roles = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/project/{project["id"]}/role', headers=HEADERS, auth=AUTH).json()

            for key, value in project_roles.items():
                role_id = value.split("role/", 1)[1]
                role = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/project/{project["id"]}/role/{role_id}', headers=HEADERS, auth=AUTH).json()

                if "(migrated)" in role['name']:
                    normal_role_name = role['name'].split(" (migrated)", 1)[0]

                    for key, value in project_roles.items():
                        if key == normal_role_name and "(migrated)" not in key:
                            normal_role_id = value.split("role/", 1)[1]
                            normal_role = requests.get(f'{CLOUD_BASE_URL}/rest/api/3/project/{project["id"]}/role/{normal_role_id}', headers=HEADERS, auth=AUTH).json()

                            for actor in role["actors"]:
                                if actor["type"] == "atlassian-group-role-actor":
                                    logging.info(f'> > > Group Name: {actor["name"]}')
                                    payload = {
                                        "groupId": [actor["actorGroup"]["groupId"]]
                                    }
                                    requests.post(f'{CLOUD_BASE_URL}/rest/api/3/project/{project["id"]}/role/{normal_role_id}', headers=HEADERS, data=json.dumps(payload), auth=AUTH)

                                if actor["type"] == "atlassian-user-role-actor":
                                    logging.info(f'> > > User Name: {actor["displayName"]}')
                                    payload = {
                                        "user": [actor["actorUser"]["accountId"]]
                                    }
                                    requests.post(f'{CLOUD_BASE_URL}/rest/api/3/project/{project["id"]}/role/{normal_role_id}', headers=HEADERS, data=json.dumps(payload), auth=AUTH)

if __name__ == "__main__":
    logging.info('Starting [Permission Schemes] cleaning...')
    clean_permission_schemes()
    logging.info('Starting [Projects] cleaning...')
    clean_projects()
