from.models.attendance import Punch,LeaveBalance
from .models.Admin_models import Admin
from .models.signup import Signup
from calendar import monthrange
from . import db
from datetime import date,timedelta,datetime
from datetime import date, timedelta,datetime



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
    Get today's punch in, punch out, and total worked time as a `time` object.
    """
    today = date.today()
    punch = Punch.query.filter_by(admin_id=user_id, punch_date=today).first()

    if punch and punch.punch_in and punch.punch_out:
        # Calculate time difference
        in_time = datetime.combine(today, punch.punch_in)
        out_time = datetime.combine(today, punch.punch_out)

        # Calculate the duration worked
        worked_duration = out_time - in_time


        # Convert duration to total seconds
        total_seconds = int(worked_duration.total_seconds())

        # Convert to hours, minutes, seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        # Convert to a time object (HH:MM:SS)
        worked_time = time(hour=hours, minute=minutes, second=seconds)
        punch.today_work = worked_time
        db.session.commit()

        return worked_time  # return as a `time` object (you can directly store it in DB)

    # If no punch or incomplete, return 00:00:00
    return time(0, 0, 0)



def get_remaining_resignation_days(resignation_date, notice_period_days=90):
    if not resignation_date:
        return None, None  # No resignation date provided

    today = date.today()
    last_working_day = resignation_date + timedelta(days=notice_period_days)
    print(last_working_day)

    if resignation_date <= today <= last_working_day:
        days = (last_working_day - today).days
        return days
    elif today > last_working_day:
        return 0, "Notice period has ended."
    elif today < resignation_date:
        return None, "Notice period has not started yet."

    return None, None
