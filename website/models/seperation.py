from datetime import datetime
from .. import db

class Resignation(db.Model):
    __tablename__ = 'resignations'

    id = db.Column(db.Integer, primary_key=True)

    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    admin = db.relationship('Admin', back_populates='resignations')

    resignation_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    applied_on = db.Column(db.DateTime, default=datetime.now())  # Use function, not datetime.now()
