from . import db
from datetime import datetime, timezone
import uuid


class CustomerContact(db.Model):
    __tablename__ = "customer_contacts"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(
        db.String(36), db.ForeignKey("customers.id"), nullable=False
    )
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer = db.relationship("Customer", back_populates="customer_contacts")
    customer_contact_comm_method = db.relationship(
        "CustomerContactCommMethod", back_populates="customer_contact", lazy=True
    )
