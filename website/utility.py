from.models.attendance import Punch
from .models.Admin_models import Admin
from .models.signup import Signup
from .models.attendance import LeaveBalance
from calendar import monthrange
from .forms.search_from import PunchManuallyForm
from flask import render_template, flash, redirect, url_for
from . import db
from datetime import date, timedelta


from datetime import date,datetime



def attend_calc(year,month,num_days,user_id):

    punches = Punch.query.filter(
        Punch.punch_date.between(f'{year}-{month:02d}-01', f'{year}-{month:02d}-{num_days}'),
        Punch.admin_id == user_id
    ).all()

    calcu_data = 0
    calcu_hdata = 0
    for pdata in punches:
        if pdata.punch_date:
            if pdata.punch_in and pdata.punch_out:
                calcu_data += 1
            elif pdata.punch_in and not pdata.punch_out:
                calcu_data += 0.5
        if pdata.is_wfh:
            calcu_hdata += 1
    return {
        "attendance": calcu_data,
        "work from home": calcu_hdata
    }




def get_user_working_summary(user_id, year, month):
    

    # 1. Get number of days in the given month
    num_days = monthrange(year, month)[1]

    # 2. Attendance and WFH calculation
    attendance_data = attend_calc(year, month, num_days, user_id)

    # 3. Get user email from Admin and find corresponding Signup
    admin = Admin.query.get(user_id)
    signup = Signup.query.filter_by(email=admin.email).first()

    # 4. Fetch PL and CL using signup_id
    leave_balance = LeaveBalance.query.filter_by(signup_id=signup.id).first() if signup else None

    # 5. Safe default values
    pl_balance = leave_balance.privilege_leave_balance if leave_balance else 0.0
    cl_balance = leave_balance.casual_leave_balance if leave_balance else 0.0

    

    return {
        "present_days": attendance_data["attendance"],
        "work_from_home_days": attendance_data["work from home"],
        "privilege_leave_balance": pl_balance,
        "casual_leave_balance": cl_balance,
        "total_working_days": num_days
    }



def punch_time(user_id):
    """
    Get today's punch in, punch out, and total worked time.
    """
    today = date.today()
    punch = Punch.query.filter_by(admin_id=user_id, punch_date=today).first()

    if punch and punch.punch_in and punch.punch_out:
        # Calculate time difference
        in_time = datetime.combine(today, punch.punch_in)
        out_time = datetime.combine(today, punch.punch_out)
        worked_duration = out_time - in_time

        # Convert to hours and minutes
        total_minutes = int(worked_duration.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"Todays work time :  {hours}h {minutes}m"

    return {
        "Todays work time": "0h 0m"
    }
