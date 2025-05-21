from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .customer import Customer
from .customer_contact import CustomerContact
from .customer_comm_method import CustomerCommMethod
from .customer_contact_comm_method import CustomerContactCommMethod
from .conversation import Conversation
from .message import Message
