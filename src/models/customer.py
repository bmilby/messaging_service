from . import db
from datetime import datetime, timezone
import uuid


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer_comm_methods = db.relationship(
        "CustomerCommMethod", back_populates="customer", lazy=True
    )
    customer_contacts = db.relationship(
        "CustomerContact", back_populates="customer", lazy=True
    )
