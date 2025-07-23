print("receive_notification.py first line")
import logging
from datetime import datetime
from json import dumps
import paths
from env_var_injection import instance_id, api_token
from whatsapp_api_client_python import API

greenAPI = API.GreenAPI(
	instance_id, api_token
)

def main():
	print(f"polling started   ")
	greenAPI.webhooks.startReceivingNotifications(handler)
	print("this will never print if startReceivingNotifications is blocking")


def handler(type_webhook: str, body: dict) -> None:
	print(f"Webhook type: {type_webhook}, Body: {body}")
	if type_webhook == "incomingMessageReceived":
		incoming_message_received(body)
	elif type_webhook == "outgoingMessageReceived":
		outgoing_message_received(body)
	elif type_webhook == "outgoingAPIMessageReceived":
		outgoing_api_message_received(body)
	elif type_webhook == "outgoingMessageStatus":
		outgoing_message_status(body)
	elif type_webhook == "stateInstanceChanged":
		state_instance_changed(body)
	elif type_webhook == "deviceInfo":
		device_info(body)
	elif type_webhook == "incomingCall":
		incoming_call(body)
	elif type_webhook == "statusInstanceChanged":
		status_instance_changed(body)


def get_notification_time(timestamp: int) -> str:
	return str(datetime.fromtimestamp(timestamp))


def incoming_message_received(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"New incoming message at {time} with data: {data}", end="\n\n")


def outgoing_message_received(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"New outgoing message at {time} with data: {data}", end="\n\n")

def outgoing_api_message_received(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"New outgoing API message at {time} with data: {data}", end="\n\n")


def outgoing_message_status(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	response = (
		f"Status of sent message has been updated at {time} with data: {data}"
	)
	print(response, end="\n\n")


def state_instance_changed(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"Current instance state at {time} with data: {data}", end="\n\n")


def device_info(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	response = (
		f"Current device information at {time} with data: {data}"
	)
	print(response, end="\n\n")

def incoming_call(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"New incoming call at {time} with data: {data}", end="\n\n")


def status_instance_changed(body: dict) -> None:
	timestamp = body["timestamp"]
	time = get_notification_time(timestamp)

	data = dumps(body, ensure_ascii=False, indent=4)

	print(f"Current instance status at {time} with data: {data}", end="\n\n")


if __name__ == '__main__':
	print("main started in receive_notification.py")
	print(f"instance_id: {instance_id}, api_token: {api_token[:4]}****")
	print("polling started")
	main()