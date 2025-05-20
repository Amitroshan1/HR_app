from .. import db
from flask_login import UserMixin
from datetime import datetime


class Punch(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    punch_date = db.Column(db.Date, nullable=False)
    punch_in = db.Column(db.Time, nullable=True)
    punch_out = db.Column(db.Time, nullable=True)
    is_holiday = db.Column(db.Boolean, default=False)  
    
    admin = db.relationship('Admin', back_populates='punch_records')



class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys for Signup and Admin
    signup_id = db.Column(db.Integer, db.ForeignKey('signups.id', ondelete="CASCADE"), unique=True, nullable=False)
    
    privilege_leave_balance = db.Column(db.Float, default=0.0, nullable=False)
    casual_leave_balance = db.Column(db.Float, default=0.0, nullable=False)

    # Relationships
    signup = db.relationship('Signup', back_populates='leave_balance')
    
    def __init__(self, signup_id, admin_id=None, privilege_leave_balance=0.0, casual_leave_balance=0.0, **kwargs):
        super().__init__(**kwargs)
        self.signup_id = signup_id
        self.admin_id = admin_id
        self.privilege_leave_balance = privilege_leave_balance
        self.casual_leave_balance = casual_leave_balance



    

class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) 
    reason = db.Column(db.String(255), nullable=False)  
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)  
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    admin = db.relationship('Admin', back_populates='leave_applications')

