from flask import abort
from typing import Optional, Any, get_origin, get_args
from datetime import datetime
import logging
import time
import traceback
import requests

logger = logging.getLogger("messaging_service")

MAX_RETRIES = 3  # number of retry attempts
RETRY_DELAY = 5  # initial retry delay in seconds


def validate_payload(
    data: dict,
    payload_fields: list[dict],
    one_of_fields: list = None,
) -> None:
    """
    Validates the incoming payload.
        - checks if the 'type' field is present and valid (either 'sms','mms', 'email').
        - checks if the required fields are present and of the correct data type.

    Args:
        data: json payload
        payload_fields: list of dicts with payload field name, data type, required flag
        one_of_fields: list of optional fields, at least one of which must be present.

    Returns:
        None
    """
    errors = []

    message_type = data.get("type")

    if not isinstance(message_type, str):
        abort(
            400,
            description=f"invalid 'type'. 'type' must be a non-empty string",
        )

    message_type = message_type.lower()
    if message_type not in ["sms", "mms", "email"]:
        abort(
            400,
            description=f"unsupported 'type' in payload. supported types are 'sms', 'mms', and 'email'",
        )

    if message_type == "email":
        check_one_of_fields(data, one_of_fields)

    # check the payload fields
    for item in payload_fields:
        field_name = item["field"]
        expected_type = item["type"]
        required_field = item["required"]
        value = data.get(field_name)

        if message_type == "sms" and field_name == "body":
            required_field = True
        elif message_type == "mms" and field_name == "attachments":
            required_field = True
        # maybe enforce mms if attachments field is provided

        if value is None:
            if required_field:
                errors.append(f"payload missing required field: {field_name}")
            continue

        # handle generic types like list[str]
        origin = get_origin(expected_type)
        if origin is list:
            item_type = get_args(expected_type)[0]
            if not isinstance(value, list) or not all(
                isinstance(x, item_type) for x in value
            ):
                errors.append(
                    f"payload field '{field_name}' must be a list of {item_type.__name__}"
                )

        # handle datetime types
        elif expected_type is datetime:
            if not isinstance(value, str):
                errors.append(
                    f"payload field '{field_name}' must be an ISO8601 string representing datetime"
                )
            else:
                try:
                    value = value.replace("Z", "+00:00") if "Z" in value else value
                    parsed = datetime.fromisoformat(value)
                except ValueError:
                    errors.append(
                        f"payload field '{field_name}' must be a valid ISO8601 datetime string"
                    )

        # handle other types
        else:
            if not isinstance(value, expected_type):
                errors.append(
                    f"payload field '{field_name}' must be of type {expected_type.__name__}"
                )

    if errors:
        abort(400, description="; ".join(errors))


def check_one_of_fields(data: dict, one_of_fields: list) -> None:
    """
    Checks that at least one field in one_of_fields is present and non-empty.
    Args:
        data: the incoming request JSON payload.
        one_of_fields: list of optional fields, at least one of which must be present.

    Returns:
        None
    """
    if one_of_fields:
        one_of_provided = False
        for field in one_of_fields:
            value = data.get(field)
            if value is not None and (
                not isinstance(value, str) or value.strip() != ""
            ):
                one_of_provided = True
                break

        if not one_of_provided:
            abort(
                400,
                description=f"one of the following fields must be provided in payload: {', '.join(one_of_fields)}",
            )


def send_message(api_url: str, message_data: dict) -> bool:
    """
    Sends a message to the specified api url

    Args:
        api_url: url to send message
        message_data: message data payload

    Returns:
        bool, true if message was sent successfully, false otherwise
    """
    message_sent = False
    try:
        response = requests.post(
            api_url,
            json=message_data,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        logger.info(f"response status code: {response.status_code}")
        logger.info(f"response json: {response.text}")

        message_sent = True

        return message_sent
    except Exception as e:
        raise e


def api_retry_with_backoff(func, *args, **kwargs):
    """
    Retries a function call with exponential backoff on timeout errors.
    Args:
        func: Function to call
        *args, **kwargs: Arguments to pass to the function

    Returns:
        the function's result if successful, or None if all retries fail.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # try calling the function
            return func(*args, **kwargs)
        except TimeoutError as e:
            logger.warning(
                f"timeout occurred in {func.__name__} (attempt {attempt}/{MAX_RETRIES}). retrying..."
            )

            # exponential backoff
            time.sleep(RETRY_DELAY * (2 ** (attempt - 1)))
        except Exception as e:
            error = traceback.format_exc()
            logger.error(f"unhandled exception in {func.__name__}: {error}")
            break  # stop retrying on non-timeout errors
    return False  # return None if all retries fail
