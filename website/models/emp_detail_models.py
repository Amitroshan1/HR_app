from .. import db
from flask_login import UserMixin





class Employee(db.Model,UserMixin):

    __tablename__ = 'employees'

    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), unique=True, nullable=False)
     
    photo_filename = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    mother_name = db.Column(db.String(100), nullable=False)
    marital_status = db.Column(db.String(20), nullable=False)
    spouse_name = db.Column(db.String(100), nullable=True)
    dob = db.Column(db.Date, nullable=False)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    mobile = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    emergency_mobile = db.Column(db.String(10), nullable=False)
    caste = db.Column(db.String(150), nullable=False)
    nationality = db.Column(db.String(150), nullable=False)
    language = db.Column(db.String(150), nullable=False)
    religion = db.Column(db.String(150), nullable=False)
    blood_group = db.Column(db.String(150), nullable=False)
    designation=db.Column(db.String(150), nullable=False)
    
    permanent_address_line1 = db.Column(db.String(200), nullable=False)
    permanent_address_line2 = db.Column(db.String(200), nullable=True)
    permanent_address_line3 = db.Column(db.String(200), nullable=True)
    permanent_pincode = db.Column(db.String(10), nullable=False)
    permanent_district = db.Column(db.String(100), nullable=True)
    permanent_state = db.Column(db.String(100), nullable=True)

    present_address_line1 = db.Column(db.String(200), nullable=False)
    present_address_line2 = db.Column(db.String(200), nullable=True)
    present_address_line3 = db.Column(db.String(200), nullable=True)
    present_pincode = db.Column(db.String(10), nullable=False)
    present_district = db.Column(db.String(100), nullable=True)
    present_state = db.Column(db.String(100), nullable=True)


    
    # One-to-One relationship with Admin
    admin = db.relationship('Admin', back_populates='employee_details')
    
    def __repr__(self):
        return f'<Employee {self.name}>'