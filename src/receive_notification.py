print("receive_notification.py first line")
from paths import logs_root
from json import dumps
from env_var_injection import instance_id, api_token
from whatsapp_api_client_python import API
from src.utils.log import get_logger, setup_logger
from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.db import get_message_by_message_id, get_user_by_whatsapp_id, get_group_by_whatsapp_id
from src.message_queue.redis_streams_queue import RedisMessageQueue
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.engine import Engine
from sqlalchemy import event

setup_logger(logs_root)
logger = get_logger("whatsapp_miner")
logger.info("Mensaje de prueba")

greenAPI = API.GreenAPI(
	instance_id, api_token
)

# Initialize queue for publishing messages
message_queue = RedisMessageQueue()

def main():
	print(f"polling started   ")
	greenAPI.webhooks.startReceivingNotifications(handler)
	print("this will never print if startReceivingNotifications is blocking")

@event.listens_for(Engine, "connect")
def print_connection_info(dbapi_connection, connection_record):
	from env_var_injection import database_url
	print(f"[DEBUG] Connecting to database: {database_url}")

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
	session = get_session_local()()

	try:
		message_id = body["idMessage"]
		timestamp = datetime.fromtimestamp(body["timestamp"])
		message_data = body.get("messageData", {})
		sender_data = body.get("senderData", {})

		# Extract correct IDs
		user_id = sender_data.get("sender")                      # "972547204581@c.us"
		user_name = sender_data.get("senderName", "")           # "Noams Original"
		group_id = sender_data.get("chatId")                    # "120363418155390035@g.us"
		group_name = sender_data.get("chatName", "")            # "Group1"

		if not group_id or not group_id.endswith("@g.us"):
			print(f"[Skip] Ignoring private message {message_id} from {user_id}")
			return

		message_type = message_data.get("typeMessage", "")
		message_text = (
			message_data.get("textMessageData", {}).get("textMessage", "") or
			message_data.get("extendedTextMessageData", {}).get("text", "")
		)
		is_forwarded = message_data.get("extendedTextMessageData", {}).get("isForwarded", False)

		# Skip messages under 8 characters
		if len(message_text.strip()) < 8:
			print(f"[Skip] Message {message_id} too short (under 8 characters): '{message_text}'")
			return

		# Skip if already exists
		if get_message_by_message_id(session, message_id):
			print(f"[Skip] Message {message_id} already in DB.")
			return

		# Upsert user
		user = get_user_by_whatsapp_id(session, user_id)
		if not user:
			user = WhatsAppUser(whatsapp_id=user_id, display_name=user_name)
			session.add(user)
			session.flush()

		# Upsert group
		group = get_group_by_whatsapp_id(session, group_id)
		if not group:
			group = WhatsAppGroup(
				whatsapp_group_id=group_id,
				group_name=group_name
			)
			session.add(group)
			session.flush()

		# Insert message
		new_msg = WhatsAppMessage(
			message_id=message_id,
			sender_id=user.id,
			group_id=group.id,
			timestamp=timestamp,
			raw_text=message_text,
			message_type=message_type,
			is_forwarded=is_forwarded,
			is_real=True,  # Messages from real WhatsApp API are real
		)
		session.add(new_msg)
		session.commit()
		print(f"[OK] Inserted group message {message_id} from user {user_id} in group {group_id}")

		# Publish message to Redis Streams for multi-environment processing
		queue_message_data = {
			'id': message_id,
			'raw_text': message_text,
			'sender_id': user_id,
			'group_id': group_id,
			'timestamp': timestamp.isoformat(),
			'message_type': message_type,
			'is_forwarded': is_forwarded,
			'user_name': user_name,
			'group_name': group_name
		}
		
		# Publish to Redis Streams (fire-and-forget)
		message_queue.publish_message(queue_message_data)
		logger.info(f"📤 Published message {message_id} to queue for multi-environment processing")

	except IntegrityError:
		session.rollback()
		print(f"[Error] Integrity issue on message {message_id}")
	except Exception as e:
		session.rollback()
		logger.error(f"❌ Failed to process message: {e}")
		print(f"[Error] Failed to insert message: {e}")
	finally:
		session.close()

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