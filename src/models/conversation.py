from . import db
from datetime import datetime, timezone
import uuid


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(
        db.String(36), db.ForeignKey("customers.id"), nullable=False
    )
    customer_contact_id = db.Column(
        db.String(36), db.ForeignKey("customer_contacts.id"), nullable=False
    )
    participants_key = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer = db.relationship("Customer", backref="conversations")
    contact = db.relationship("CustomerContact", backref="conversations")
    messages = db.relationship("Message", back_populates="conversation", lazy=True)
