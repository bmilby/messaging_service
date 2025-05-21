from flask import Flask, request, jsonify
from datetime import datetime
from waitress import serve
import os
import logging
import json
from dateutil import parser

from utils.util import validate_payload, send_message, api_retry_with_backoff
from utils.db_util import (
    create_sample_data,
    get_customer_comm_method_id,
    get_customer_contact_comm_method_id,
    get_conversation_id,
    save_message,
)
from models import db, Message, Conversation

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("messaging_service")

# configure the database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "db", "messaging_service.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# initialize the database
db.init_app(app)

with app.app_context():
    db.create_all()
    create_sample_data()


SMS_PAYLOAD_FIELDS = [
    {"field": "from", "type": str, "required": True},
    {"field": "to", "type": str, "required": True},
    {"field": "type", "type": str, "required": True},
    {"field": "messaging_provider_id", "type": str, "required": True},
    {"field": "timestamp", "type": datetime, "required": True},
    {"field": "body", "type": str, "required": False},
    {"field": "attachments", "type": list[str], "required": False},
]
SMS_OUTBOUND_URL = "https://www.provider.app/api/messages"
SMS_OUTBOUND_URL = "https://webhook.site/957367cc-5c8d-44c8-a27e-71ecb2098747"

EMAIL_PAYLOAD_FIELDS = [
    {"field": "from", "type": str, "required": True},
    {"field": "to", "type": str, "required": True},
    {"field": "xillio_id", "type": str, "required": True},
    {"field": "timestamp", "type": datetime, "required": True},
    {"field": "body", "type": str, "required": False},
    {"field": "attachments", "type": list[str], "required": False},
]
EMAIL_OUTBOUND_URL = "https://www.mailplus.app/api/email"
EMAIL_OUTBOUND_URL = "https://webhook.site/957367cc-5c8d-44c8-a27e-71ecb2098747"


# routes
@app.route("/api/inbound_sms", methods=["POST"])
def inbound_sms():
    logger.info("inbound_sms")

    data = request.get_json()
    if data is None:
        return jsonify({"error": "missing json payload"}), 400

    payload_fields = SMS_PAYLOAD_FIELDS.copy()
    return process_inbound_message(data, "phone", payload_fields)


@app.route("/api/outbound_sms", methods=["POST"])
def outbound_sms():
    logger.info(f"outbound_sms")

    data = request.get_json()
    if data is None:
        return jsonify({"error": "missing json payload"}), 400

    payload_fields = SMS_PAYLOAD_FIELDS.copy()
    payload_fields = [
        f for f in payload_fields if f["field"] != "messaging_provider_id"
    ]
    return process_outbound_message(data, "phone", payload_fields, SMS_OUTBOUND_URL)


@app.route("/api/inbound_email", methods=["POST"])
def inbound_email():
    logger.info("inbound_email")

    data = request.get_json()
    if data is None:
        return jsonify({"error": "missing json payload"}), 400

    data["type"] = "email"

    payload_fields = EMAIL_PAYLOAD_FIELDS.copy()
    return process_inbound_message(
        data, "email", payload_fields, ["body", "attachments"]
    )


@app.route("/api/outbound_email", methods=["POST"])
def outbound_email():
    logger.info("outbound_email")

    data = request.get_json()
    if data is None:
        return jsonify({"error": "missing json payload"}), 400

    data["type"] = "email"

    payload_fields = EMAIL_PAYLOAD_FIELDS.copy()
    payload_fields = [f for f in payload_fields if f["field"] != "xillio_id"]
    return process_outbound_message(data, "email", payload_fields, EMAIL_OUTBOUND_URL)


def process_inbound_message(
    data: dict,
    comm_type: str,
    payload_fields: list[dict],
    optional_fields: list = None,
) -> tuple:
    """
    Process inbound sms or email messages
    Args:
        data: json payload
        comm_type: communication method (email, phone)
        payload_fields: list of dicts with payload field name, data type, required flag
        optional_fields: list of optional fields, at least one of which must be present.

    Returns:
        tuple containing (response, status code)
    """
    try:
        logger.info(f"received inbound payload: {data}")

        validate_payload(data, payload_fields, optional_fields)

        (
            customer_comm_method_id,
            contact_comm_method_id,
            customer_id,
            customer_contact_id,
            participants_key,
        ) = get_participants(data, "inbound", comm_type)

        conversation_id = get_conversation_id(
            customer_id, customer_contact_id, participants_key
        )
        message = create_message(
            data,
            conversation_id,
            customer_comm_method_id,
            contact_comm_method_id,
            "inbound",
            comm_type,
        )

        return (
            jsonify(
                {"status": "message received successfully", "message_id": message.id}
            ),
            200,
        )
    except Exception as e:
        message = f"error processing inbound {comm_type} payload: {e}"
        logger.error(message)
        return jsonify({"error": message}), 400


def process_outbound_message(
    data: dict, comm_type: str, payload_fields: list[dict], outbound_url: str
) -> tuple:
    """
    Process outbound sms or email messages
    Args:

        data: json payload
        comm_type: communication method (email, phone)
        payload_fields: list of dicts with payload field name, data type, required flag
        outbound_url: url to send message

    Returns:
        tuple containing (response, status code)
    """
    try:
        logger.info(f"received outbound payload: {data}")

        validate_payload(data, payload_fields)

        (
            customer_comm_method_id,
            contact_comm_method_id,
            customer_id,
            customer_contact_id,
            participants_key,
        ) = get_participants(data, "outbound", comm_type)

        message_sent = api_retry_with_backoff(send_message, outbound_url, data)
        if not message_sent:
            logger.error(f"message failed to send to outbound url{outbound_url}")
            return (
                jsonify(
                    {
                        "status": "message failed to send",
                        "error": "failed to send message",
                    }
                ),
                500,
            )

        logger.info("message sent successfully")
        conversation_id = get_conversation_id(
            customer_id, customer_contact_id, participants_key
        )
        message = create_message(
            data,
            conversation_id,
            customer_comm_method_id,
            contact_comm_method_id,
            "outbound",
            comm_type,
        )

        return (
            jsonify({"status": "message sent successfully", "message_id": message.id}),
            200,
        )
    except Exception as e:
        message = f"error processing outbound {comm_type} payload: {e}"
        logger.error(message)
        return jsonify({"error": message}), 400


def get_participants(data: dict, message_direction: str, comm_type: str) -> tuple:
    """
    Get participants for the message
    Args:
        data: json payload
        message_direction: direction of the message (inbound or outbound)
        comm_type: communication method (email, phone)

    Returns:
        tuple containing customer communication method id, contact communication method id,
        customer id, customer contact id, and participants key
    """

    from_address = data.get("from")
    to_address = data.get("to")

    customer_comm_method_id, customer_id = get_customer_comm_method_id(
        comm_type, to_address if message_direction == "inbound" else from_address
    )
    contact_comm_method_id, customer_contact_id = get_customer_contact_comm_method_id(
        customer_id,
        comm_type,
        from_address if message_direction == "inbound" else to_address,
    )
    participants_key = ",".join(sorted([customer_id, customer_contact_id]))
    return (
        customer_comm_method_id,
        contact_comm_method_id,
        customer_id,
        customer_contact_id,
        participants_key,
    )


def create_message(
    data: dict,
    conversation_id: str,
    customer_comm_method_id: str,
    contact_comm_method_id: str,
    message_direction: str,
    comm_type: str,
) -> Message:
    """
    Create a message object and save it to the database
    Args:
        data: json payload
        conversation_id: id of the conversation
        customer_comm_method_id: id of the customer communication method
        contact_comm_method_id: id of the contact communication method
        message_direction: direction of the message (inbound or outbound)
        comm_type: communication method (email, phone)

    Returns:
        message object
    """
    messaging_provider_id = data.get(
        "messaging_provider_id" if comm_type == "phone" else "xillio_id"
    )
    message_type = data.get("type")
    body = data.get("body")
    attachments = (
        json.dumps(data.get("attachments"))
        if data.get("attachments") is not None
        else None
    )
    timestamp = datetime.fromisoformat(data.get("timestamp").replace("Z", "+00:00"))

    message = Message(
        conversation_id=conversation_id,
        to_customer_comm_id=(
            customer_comm_method_id if message_direction == "inbound" else None
        ),
        from_customer_comm_id=(
            customer_comm_method_id if message_direction == "outbound" else None
        ),
        from_contact_comm_id=(
            contact_comm_method_id if message_direction == "inbound" else None
        ),
        to_contact_comm_id=(
            contact_comm_method_id if message_direction == "outbound" else None
        ),
        messaging_provider_id=messaging_provider_id,
        message_type=message_type,
        body=body,
        attachments=attachments,
        timestamp=timestamp,
    )
    save_message(message)
    return message


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)
