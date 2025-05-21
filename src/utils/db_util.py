from datetime import datetime, timezone
import uuid
from sqlalchemy import text

from models import db
from models.contact_type import ContactType
from models.customer_contact import CustomerContact
from models.customer_contact_comm_method import CustomerContactCommMethod
from models.conversation import Conversation
from models.message import Message


def get_customer_comm_method_id(comm_type: str, value: str) -> tuple[str, str]:
    """
    Gets the customer communication method id and customer id

    Args:
        comm_type: communication method (email, phone)
        value: value of the communication method (email address, phone number)

    Returns:
        tuple containing the customer communication method id and customer id
    """

    comm_type = comm_type.strip().lower()
    value = value.strip()

    query = text(
        """
        SELECT 
                id,
                customer_id
        FROM customer_comm_methods
        WHERE type = :comm_type
        AND value = :value
    """
    )

    result = db.session.execute(
        query, {"comm_type": comm_type, "value": value}
    ).fetchall()

    if not result:
        raise ValueError(f"customer communication method not found for value: {value}")
    elif len(result) > 1:
        raise ValueError(
            f"multiple customer communication methods found for the same value: {value}"
        )

    return result[0]


def get_customer_contact_comm_method_id(
    customer_id: str, comm_type: str, value: str
) -> tuple[str, str]:
    """
    Gets the customer communication method id and customer id or creates a new one if the contact
    is a rando

    Args:
        customer_id: id of the customer
        comm_type: communication method (email, phone)
        value: value of the communication method (email address, phone number)

    Returns:
        tuple containing the customer contact communication method id and customer contact id
    """

    comm_type = comm_type.strip().lower()
    value = value.strip()

    query = text(
        """
        SELECT
                cm.id,
                cm.customer_contact_id
        FROM customer_contact_comm_methods cm
        INNER JOIN customer_contacts cc ON cc.id = cm.customer_contact_id
        WHERE cc.customer_id = :customer_id
        AND cm.type = :comm_type
        AND cm.value = :value
    """
    )

    result = db.session.execute(
        query, {"customer_id": customer_id, "comm_type": comm_type, "value": value}
    ).fetchall()

    if len(result) > 1:
        raise ValueError(
            f"multiple customer contacts communication methods found for the same value: {value}"
        )

    if result:
        return result[0]

    # create new customer contact
    new_contact = CustomerContact(
        customer_id=customer_id,
        first_name=None,
        last_name=None,
    )
    db.session.add(new_contact)
    db.session.flush()

    # create new customer contact comm method
    new_comm = CustomerContactCommMethod(
        customer_contact_id=new_contact.id,
        type=ContactType(comm_type),
        value=value,
    )
    db.session.add(new_comm)
    db.session.commit()

    return new_comm.id, new_contact.id


def get_conversation_id(
    customer_id: str, customer_contact_id: str, participants_key: str
) -> str:
    """
    Gets the conversation id or creates a new one if it doesn't exist

    Args:
        customer_id: id of the customer
        customer_contact_id: id of the customer contact
        participants_key: key to identify the conversation

    Returns:
        string containing the conversation id
    """

    query = text(
        """
        SELECT
                id
        FROM conversations
        WHERE participants_key = :participants_key
    """
    )

    result = db.session.execute(
        query, {"participants_key": participants_key}
    ).fetchall()

    if len(result) > 1:
        raise ValueError(
            f"multiple conversations found for participants key: {participants_key}"
        )

    if result:
        return result[0].id

    # create new conversation
    new_conversation = Conversation(
        customer_id=customer_id,
        customer_contact_id=customer_contact_id,
        participants_key=participants_key,
    )
    db.session.add(new_conversation)
    db.session.commit()

    return new_conversation.id


def save_message(message: Message) -> None:
    """
    Saves message to the database

    Args:
        message: Message object to be saved

    Returns:
        None
    """
    # insert new Message
    db.session.add(message)
    db.session.commit()


def create_sample_data():
    # check if sample data already exists
    existing = db.session.execute(text("SELECT id FROM customers LIMIT 1")).fetchone()
    if existing:
        return

    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)

    customer1_id = str(uuid.uuid4())
    db.session.execute(
        text(
            f"""
                INSERT INTO customers (id, name, created_at)
                VALUES ('{customer1_id}', 'Keystone Carpentry', '{now_naive}')
            """
        )
    )
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_comm_methods (id, customer_id, type, value, label, created_at)
        VALUES
        ('{uuid.uuid4()}', '{customer1_id}', 'phone', '+12155550000', 'main phone number', '{now_naive}'),
        ('{uuid.uuid4()}', '{customer1_id}', 'email', 'info@keystonecarpentry.com', 'main email', '{now_naive}'),
        ('{uuid.uuid4()}', '{customer1_id}', 'whatsapp', '+12155550000', 'whatsapp number', '{now_naive}')
    """
        )
    )
    identity1_id = str(uuid.uuid4())
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_contacts (id, customer_id, first_name, last_name, created_at)
        VALUES ('{identity1_id}', '{customer1_id}', 'Jane', 'Doe', '{now_naive}')
    """
        )
    )
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_contact_comm_methods (id, customer_contact_id, type, value, created_at)
        VALUES 
        ('{uuid.uuid4()}', '{identity1_id}', 'phone', '+15551230001', '{now_naive}'),
        ('{uuid.uuid4()}', '{identity1_id}', 'email', 'janed@gmail.com', '{now_naive}')
    """
        )
    )

    customer2_id = str(uuid.uuid4())
    db.session.execute(
        text(
            f"""
        INSERT INTO customers (id, name, created_at)
        VALUES ('{customer2_id}', 'Hydro NYC', '{now_naive}')
    """
        )
    )
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_comm_methods (id, customer_id, type, value, label, created_at)
        VALUES 
        ('{uuid.uuid4()}', '{customer2_id}', 'phone', '+12155551111', 'main number', '{now_naive}'),
        ('{uuid.uuid4()}', '{customer2_id}', 'email', 'info@hydronyc.com', 'main email', '{now_naive}')
    """
        )
    )
    identity2_id = str(uuid.uuid4())
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_contacts (id, customer_id, first_name, last_name, created_at)
        VALUES ('{identity2_id}', '{customer2_id}', 'John', 'Doe', '{now_naive}')
    """
        )
    )
    db.session.execute(
        text(
            f"""
        INSERT INTO customer_contact_comm_methods (id, customer_contact_id, type, value, created_at)
        VALUES 
        ('{uuid.uuid4()}', '{identity2_id}', 'phone', '+15551230002', '{now_naive}')
    """
        )
    )

    db.session.commit()
