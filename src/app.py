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


def choose_customer(customers):
    print("Unique customers:")
    for i, customer in enumerate(customers):
        print(f"{i + 1}. {customer}")
    choice = int(input("Choose a customer by entering the corresponding number: "))
    return customers[choice - 1]


def copy_or_update_folder(space_id, folder, chosen_customer):
    new_folder_name = f"Planning - {chosen_customer}"
    existing_folder = get_folder(space_id, new_folder_name)

    if not existing_folder:
        # Create a new folder
        response = requests.post(
            f"https://api.clickup.com/api/v2/space/{space_id}/folder",
            json={"name": new_folder_name},
            headers=headers,
        )
        response.raise_for_status()
        copied_folder_id = response.json()["id"]
    else:
        # Update the existing folder
        copied_folder_id = existing_folder["id"]

    for lst in folder["lists"]:
        response = requests.post(
            f"https://api.clickup.com/api/v2/folder/{copied_folder_id}/list",
            json={"name": lst["name"]},
            headers=headers,
        )
        response.raise_for_status()
        copied_list_id = response.json()["id"]

        response = requests.get(
            f"https://api.clickup.com/api/v2/list/{lst['id']}/task", headers=headers
        )
        response.raise_for_status()
        tasks = response.json()["tasks"]

        for task in tasks:
            for field in task["custom_fields"]:
                if field["name"] == "Customer" and "value" in field:
                    if field["value"] == chosen_customer:
                        response = requests.post(
                            f"https://api.clickup.com/api/v2/list/{copied_list_id}/task",
                            json={
                                "name": task["name"],
                                "custom_fields": task["custom_fields"],
                            },
                            headers=headers,
                        )
                        response.raise_for_status()
                    else:
                        response = requests.post(
                            f"https://api.clickup.com/api/v2/list/{copied_list_id}/task",
                            json={"name": "Generic Task"},
                            headers=headers,
                        )
                        response.raise_for_status()
                    break


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
