from . import db
from datetime import datetime, timezone
import uuid

from models.contact_type import ContactType


class CustomerCommMethod(db.Model):
    __tablename__ = "customer_comm_methods"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(
        db.String(36), db.ForeignKey("customers.id"), nullable=False
    )
    type = db.Column(db.Enum(ContactType), nullable=False)
    value = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(20), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer = db.relationship("Customer", back_populates="customer_comm_methods")

    __table_args__ = (
        db.UniqueConstraint(
            "customer_id", "type", "value", name="uq_customer_comm_type_value"
        ),
    )
