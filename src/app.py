from dotenv import load_dotenv
import os
import requests
from requests.structures import CaseInsensitiveDict


def get_user():
    response = requests.get(f"{base_url}/user", headers=headers)
    response.raise_for_status()
    return response.json()["user"]


def get_team_id(user):
    response = requests.get(f"{base_url}/team", headers=headers)
    teams = response.json()["teams"]
    if teams:
        return teams[0]["id"]
    else:
        raise ValueError("No teams found for the user")


def get_spaces(team_id):
    response = requests.get(f"{base_url}/team/{team_id}/space", headers=headers)
    response.raise_for_status()
    return response.json()["spaces"]


def get_folders(space_id):
    response = requests.get(f"{base_url}/space/{space_id}/folder", headers=headers)
    response.raise_for_status()
    return response.json()["folders"]


def get_planning_folder(space_id):
    folders = get_folders(space_id)
    for folder in folders:
        if folder["name"] == "Planning":
            return folder
    raise ValueError("No 'Planning' folder found in the selected space")


def get_lists(folder_id):
    response = requests.get(f"{base_url}/folder/{folder_id}/list", headers=headers)
    response.raise_for_status()
    return response.json()["lists"]


def find_existing_folder(space_id, folder_name):
    existing_folders = get_folders(space_id)
    for existing_folder in existing_folders:
        if existing_folder["name"] == folder_name:
            return existing_folder
    return None


def create_folder(space_id, folder_name):
    payload = {"name": folder_name}
    response = requests.post(
        f"{base_url}/space/{space_id}/folder", headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()["id"]


def create_list(folder_id, list_name):
    payload = {"name": list_name}
    response = requests.post(
        f"{base_url}/folder/{folder_id}/list", headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()["id"]


def get_tasks(list_id):
    response = requests.get(f"{base_url}/list/{list_id}/task", headers=headers)
    response.raise_for_status()
    return response.json()["tasks"]


def create_task(list_id, task_data):
    payload = {
        "name": task_data["name"],
        "status": task_data["status"]["status"],
        "start_date": task_data["start_date"],
        "due_date": task_data["due_date"],
        "assignees": task_data["assignees"],
        "custom_fields": task_data["custom_fields"],
    }
    response = requests.post(
        f"{base_url}/list/{list_id}/task", headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()["id"]


def get_unique_customers(folder):
    customers = set()
    for list_data in folder["lists"]:
        tasks = get_tasks(list_data["id"])
        for task in tasks:
            for field in task["custom_fields"]:
                if (
                    field["name"] == "Customer"
                    and field["type"] == "text"
                    and field.get("value")
                ):
                    customers.add(field["value"])
    return customers


def copy_or_update_tasks(space_id, folder, chosen_customer, copied_list_ids):
    project_counter = 1

    for list_data in folder["lists"]:
        original_list_id = list_data["id"]
        copied_list_id = copied_list_ids[original_list_id]

        # Clear out the tasks in the copied list
        existing_tasks = get_tasks(copied_list_id)
        for task in existing_tasks:
            response = requests.delete(f"{base_url}/task/{task['id']}", headers=headers)
            response.raise_for_status()

        # Copy tasks to the copied list
        tasks = get_tasks(original_list_id)
        for task in tasks:
            customer_field = next(
                (
                    field
                    for field in task["custom_fields"]
                    if field["name"] == "Customer" and field["type"] == "text"
                ),
                None,
            )

            if customer_field and customer_field.get("value") == chosen_customer:
                create_task(copied_list_id, task)
            else:
                generic_task_data = {
                    "name": f"Project {project_counter}",
                    "status": task["status"],
                    "start_date": task["start_date"],
                    "due_date": task["due_date"],
                    "assignees": [user["id"] for user in task["assignees"]],
                    "custom_fields": [
                        {"id": field["id"], "value": ""}
                        for field in task["custom_fields"]
                    ],
                }
                create_task(copied_list_id, generic_task_data)
                project_counter += 1


def get_or_create_customer_views_folder(space_id):
    folders = get_folders(space_id)
    customer_views_folder_name = "Planning - Customer Views"
    for folder in folders:
        if folder["name"] == customer_views_folder_name:
            return folder["id"]

    # Create the folder if it doesn't exist
    response = requests.post(
        f"{base_url}/space/{space_id}/folder",
        headers=headers,
        json={"name": customer_views_folder_name},
    )
    response.raise_for_status()
    return response.json()["id"]


def get_or_create_lists_for_customer(
    customer_views_folder_id, original_folder, chosen_customer
):
    # Get existing lists
    response = requests.get(
        f"{base_url}/folder/{customer_views_folder_id}/list", headers=headers
    )
    response.raise_for_status()
    existing_lists = response.json()["lists"]

    # Check if the list for the chosen customer exists
    list_ids_mapping = {}
    for original_list in original_folder["lists"]:
        list_name = f"{original_list['name']} - {chosen_customer}"
        list_id = None
        for existing_list in existing_lists:
            if existing_list["name"] == list_name:
                list_id = existing_list["id"]
                break

        if not list_id:
            # Create the list if it doesn't exist
            response = requests.post(
                f"{base_url}/folder/{customer_views_folder_id}/list",
                headers=headers,
                json={"name": list_name},
            )
            response.raise_for_status()
            list_id = response.json()["id"]

        list_ids_mapping[original_list["id"]] = list_id

    return list_ids_mapping


if __name__ == "__main__":
    # Use your personal access token
    load_dotenv()
    api_key = os.environ.get("CLICKUP_API_TOKEN")
    if not api_key:
        raise ValueError("No API token found")

    # api_key = "your_api_key"
    base_url = "https://api.clickup.com/api/v2"
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = api_key

    # Get user data
    user = get_user()
    team_id = get_team_id(user)
    # Get spaces
    spaces = get_spaces(team_id)
    print("Select a space:")
    for i, space in enumerate(spaces):
        print(f"{i + 1}. {space['name']}")

    selected_space_index = int(input("Enter the space number: ")) - 1
    space_id = spaces[selected_space_index]["id"]

    # Get folder and its lists
    folder = get_planning_folder(space_id)
    print(f"Folder 'Planning' found with {len(folder['lists'])} lists")

    # Get unique customers from folder
    unique_customers = get_unique_customers(folder)
    print("Unique customers found:")
    for i, customer in enumerate(unique_customers):
        print(f"{i + 1}. {customer}")

    chosen_customer_index = (
        int(input("Enter the customer number to copy tasks for: ")) - 1
    )
    chosen_customer = list(unique_customers)[chosen_customer_index]

    # Check if the 'Planning - Customer Views' folder exists, create it if not
    customer_views_folder_id = get_or_create_customer_views_folder(space_id)

    # Check if the list for the chosen customer exists, create it if not
    copied_list_ids = get_or_create_lists_for_customer(
        customer_views_folder_id, folder, chosen_customer
    )

    # Copy or update tasks in the chosen customer's list
    copy_or_update_tasks(space_id, folder, chosen_customer, copied_list_ids)

    print(f"Tasks have been copied/updated for the customer '{chosen_customer}'")
