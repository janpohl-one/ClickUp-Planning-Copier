from dotenv import load_dotenv
import os
import requests

api_token = os.getenv("CLICKUP_API_TOKEN")
if not api_token:
    raise ValueError("Please set the CLICKUP_API_TOKEN environment variable")

headers = {"Authorization": api_token, "Content-Type": "application/json"}


def get_space_id(space_name):
    response = requests.get("https://api.clickup.com/api/v2/team", headers=headers)
    response.raise_for_status()
    team_id = response.json()["teams"][0]["id"]

    response = requests.get(
        f"https://api.clickup.com/api/v2/team/{team_id}/space", headers=headers
    )
    response.raise_for_status()
    spaces = response.json()["spaces"]

    for space in spaces:
        if space["name"] == space_name:
            return space["id"]
    return None


def get_folder(space_id, folder_name):
    response = requests.get(
        f"https://api.clickup.com/api/v2/space/{space_id}/folder", headers=headers
    )
    response.raise_for_status()
    folders = response.json()["folders"]

    for folder in folders:
        if folder["name"] == folder_name:
            return folder
    return None


def get_custom_field_value(task, field_name):
    custom_fields = task.get("custom_fields", [])
    for field in custom_fields:
        if field["name"] == field_name:
            return field.get("value")
    return None


def create_task(list_id, task_data):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    headers = {
        "Authorization": api_token,
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=task_data)
    response.raise_for_status()
    return response.json()


def get_unique_customers(folder):
    customers = set()
    for lst in folder["lists"]:
        response = requests.get(
            f"https://api.clickup.com/api/v2/list/{lst['id']}/task", headers=headers
        )
        response.raise_for_status()
        tasks = response.json()["tasks"]

        for task in tasks:
            for field in task["custom_fields"]:
                if field["name"] == "Customer" and "value" in field:
                    customers.add(field["value"])
                    break
    return list(customers)


def delete_task(task_id):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {
        "Authorization": api_token,
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def get_tasks_from_list(list_id):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task?archived=false"
    headers = {
        "Authorization": api_token,
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["tasks"]


def clear_tasks(list_id):
    tasks = get_tasks_from_list(list_id)
    for task in tasks:
        delete_task(task["id"])


def choose_customer(customers):
    print("Unique customers:")
    for i, customer in enumerate(customers):
        print(f"{i + 1}. {customer}")
    choice = int(input("Choose a customer by entering the corresponding number: "))
    return customers[choice - 1]


def create_generic_tasks(tasks, chosen_customer, copied_list_id):
    generic_task_count = 1
    for task in tasks:
        customer = get_custom_field_value(task, "Customer")
        if customer != chosen_customer:
            task_data = {
                "name": f"Project {generic_task_count}",
                "start_date": task["start_date"],
                "due_date": task["due_date"],
                "assignees": ",".join(str(user_id) for user_id in task["assignees"]),
                "status": task["status"]["status"],
            }
            create_task(copied_list_id, task_data)
            generic_task_count += 1


def copy_or_update_tasks(space_id, folder, chosen_customer, list_ids_mapping):
    for original_list_id, copied_list_id in list_ids_mapping.items():
        tasks = get_tasks_from_list(original_list_id)
        clear_tasks(copied_list_id)
        for task in tasks:
            customer = get_custom_field_value(task, "Customer")
            if customer == chosen_customer:
                task_data = {
                    "name": task["name"],
                    "start_date": task["start_date"],
                    "due_date": task["due_date"],
                    "assignees": ",".join(
                        str(user_id) for user_id in task["assignees"]
                    ),
                    "status": task["status"]["status"],
                }
                create_task(copied_list_id, task_data)
        create_generic_tasks(tasks, chosen_customer, copied_list_id)


def get_or_create_customer_views_folder(
    space_id, folder_name="Planning - Customer Views"
):
    folders = get_folders(space_id)
    for folder in folders:
        if folder["name"] == folder_name:
            return folder

    return create_folder(space_id, folder_name)


def get_or_create_lists_for_customer(folder, customer_name):
    existing_lists = get_lists(folder["id"])
    for lst in existing_lists:
        if lst["name"] == customer_name:
            return lst

    return create_list(folder["id"], customer_name)


if __name__ == "__main__":
    space_name = "Your Space Name"  # Replace this with your Space name
    folder_name = "Planning"

    space_id = get_space_id(space_name)
    if space_id is None:
        print(f"Space '{space_name}' not found.")
        exit(1)

    folder = get_folder(space_id, folder_name)
    if folder is None:
        print(f"Folder '{folder_name}' not found.")
        exit(1)

    unique_customers = get_unique_customers(folder)
    chosen_customer = choose_customer(unique_customers)

    copy_or_update_folder(space_id, folder, chosen_customer)

    customer_views_folder_id = get_or_create_customer_views_folder(space_id)
    copied_list_ids = get_or_create_lists_for_customer(
        customer_views_folder_id, folder, chosen_customer
    )
    copy_or_update_tasks(space_id, folder, chosen_customer, copied_list_ids)
