from website import db

class ManagerContact(db.Model):
    __tablename__ = 'manager_contacts'

    id = db.Column(db.Integer, primary_key=True)
    circle_name = db.Column(db.String(50), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    l1_name = db.Column(db.String(100), nullable=True)
    l1_mobile = db.Column(db.String(15), nullable=True)
    l1_email = db.Column(db.String(100), nullable=True)
    l2_name = db.Column(db.String(100), nullable=False)
    l2_mobile = db.Column(db.String(15), nullable=False)
    l2_email = db.Column(db.String(100), nullable=False)
    l3_name = db.Column(db.String(100), nullable=False)
    l3_mobile = db.Column(db.String(15), nullable=False)
    l3_email = db.Column(db.String(100), nullable=False)



 