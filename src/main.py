# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import paths
from src.env_var_injection import api_token, instance_id
import requests
from whatsapp_api_client_python import API


api_url = f'https://7105.api.greenapi.com/waInstance{instance_id}/receiveNotification/{api_token}'

def receive_message():
	response = requests.get(api_url)
	if response.status_code == 200:
		data = response.json()
		if data:
			print("📥 Incoming message:", data)
		else:
			print("No new messages.")
	else:
		print("Failed to poll GreenAPI:", response.status_code, response.text)
		print(f"{api_url}")

def print_hi(name):
	# Use a breakpoint in the code line below to debug your script.
	print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
	receive_message()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
