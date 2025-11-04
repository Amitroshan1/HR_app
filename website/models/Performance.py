from .. import db
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


class EmployeePerformance(db.Model):
    """
    Stores monthly performance submissions.
    Linked only to Admin (Manager/TL) for review.
    """
    __tablename__ = 'employee_performance'

    id = db.Column(db.Integer, primary_key=True)

    # --- Foreign Key (Admin who reviews) ---
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)

    # --- Performance Fields ---
    employee_name = db.Column(db.String(150), nullable=False)  # instead of employee_id
    month = db.Column(db.String(50), nullable=False)  # e.g. 'October 2025'
    achievements = db.Column(db.Text, nullable=False)
    challenges = db.Column(db.Text, nullable=True)
    goals_next_month = db.Column(db.Text, nullable=True)
    suggestion_improvement = db.Column(db.Text, nullable=True)

    # --- Metadata ---
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending / Reviewed

    # --- Relationship ---
    admin = db.relationship('Admin', backref=db.backref('performances', lazy='dynamic'))

    # --- Unique Constraint (one form per person per month) ---
    __table_args__ = (
        db.UniqueConstraint('employee_name', 'month', name='uq_employee_month'),
    )

    def __repr__(self):
        return f"<EmployeePerformance id={self.id} name={self.employee_name} month={self.month} status={self.status}>"
