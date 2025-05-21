from . import db
from datetime import datetime, timezone
import uuid

from models.contact_type import ContactType


class CustomerContactCommMethod(db.Model):
    __tablename__ = "customer_contact_comm_methods"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_contact_id = db.Column(
        db.String, db.ForeignKey("customer_contacts.id"), nullable=False
    )
    type = db.Column(db.Enum(ContactType), nullable=False)
    value = db.Column(db.String, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer_contact = db.relationship(
        "CustomerContact", back_populates="customer_contact_comm_method"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "customer_contact_id", "type", "value", name="uq_contact_comm_type_value"
        ),
    )
