from . import db
from datetime import datetime, timezone
import uuid


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("conversations.id"), nullable=False
    )

    from_customer_comm_id = db.Column(
        db.String(36), db.ForeignKey("customer_comm_methods.id"), nullable=True
    )
    to_customer_comm_id = db.Column(
        db.String(36), db.ForeignKey("customer_comm_methods.id"), nullable=True
    )

    from_contact_comm_id = db.Column(
        db.String(36), db.ForeignKey("customer_contact_comm_methods.id"), nullable=True
    )
    to_contact_comm_id = db.Column(
        db.String(36), db.ForeignKey("customer_contact_comm_methods.id"), nullable=True
    )

    messaging_provider_id = db.Column(db.String(100), nullable=True)

    message_type = db.Column(db.String(10), nullable=False)
    body = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.Text, nullable=True)  # json string of attachments
    timestamp = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    conversation = db.relationship("Conversation", back_populates="messages")

    from_contact = db.relationship(
        "CustomerContactCommMethod", foreign_keys=[from_contact_comm_id]
    )
    to_contact = db.relationship(
        "CustomerContactCommMethod", foreign_keys=[to_contact_comm_id]
    )

    from_customer_comm = db.relationship(
        "CustomerCommMethod", foreign_keys=[from_customer_comm_id]
    )
    to_customer_comm = db.relationship(
        "CustomerCommMethod", foreign_keys=[to_customer_comm_id]
    )
