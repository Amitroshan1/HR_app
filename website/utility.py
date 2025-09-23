from .models.attendance import Punch, LeaveBalance, LeaveApplication
from .models.Admin_models import Admin
from .models.signup import Signup
from calendar import monthrange
from . import db
from datetime import date, timedelta, datetime, time
from datetime import datetime
from sqlalchemy import extract, func
from sqlalchemy import func, extract, and_


def attend_calc(year, month, num_days, user_id):
    # ✅ Get punches for the month
    punches = Punch.query.filter(
        Punch.punch_date.between(f'{year}-{month:02d}-01', f'{year}-{month:02d}-{num_days}'),
        Punch.admin_id == user_id
    ).all()

    # ✅ Get approved leaves for the month
    leaves = LeaveApplication.query.filter(
        LeaveApplication.admin_id == user_id,
        LeaveApplication.status == 'Approved',
        LeaveApplication.start_date <= f'{year}-{month:02d}-{num_days}',
        LeaveApplication.end_date >= f'{year}-{month:02d}-01'
    ).all()

    calcu_data = 0
    calcu_hdata = 0
    leave_days = 0

    # ✅ Attendance + WFH
    for pdata in punches:
        if pdata.punch_date:
            if pdata.punch_in and pdata.punch_out:
                calcu_data += 1
            elif pdata.punch_in and not pdata.punch_out:
                calcu_data += 0.5
        if pdata.is_wfh:
            calcu_hdata += 1

    # ✅ Count leave days
    for leave in leaves:
        current_date = leave.start_date
        while current_date <= leave.end_date:
            if current_date.month == month and current_date.year == year:  # restrict to selected month
                leave_days += 1
            current_date += timedelta(days=1)

    return {
        "attendance": calcu_data,
        "work from home": calcu_hdata,
        "leave days": leave_days
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




@staticmethod
def add_comp_off(signup_id):
    today = datetime.today().date()  # only date part
    year, month = today.year, today.month

    leave_balance = LeaveBalance.query.filter_by(signup_id=signup_id).first()

    if leave_balance:
        # Prevent multiple additions on same day
        if leave_balance.last_updated == today:
            return  # already given today, do nothing

        if leave_balance.last_updated and leave_balance.last_updated.year == year and leave_balance.last_updated.month == month:
            if leave_balance.compensatory_leave_balance < 2:
                leave_balance.compensatory_leave_balance += 1
                leave_balance.last_updated = today
        else:
            leave_balance.compensatory_leave_balance = 1
            leave_balance.last_updated = today
    else:
        leave_balance = LeaveBalance(
            signup_id=signup_id,
            compensatory_leave_balance=1,
            last_updated=today
        )
        db.session.add(leave_balance)

    db.session.commit()





def get_total_working_days(admin_id):
    today = datetime.today()
    year, month = today.year, today.month

    # ✅ Count working days in Punch table for current month
    working_days = (
        db.session.query(func.count(Punch.id))
        .filter(
            Punch.admin_id == admin_id,
            extract('year', Punch.punch_date) == year,
            extract('month', Punch.punch_date) == month,
            Punch.today_work.isnot(None)  # only count if today_work exists
        )
        .scalar()
    )

    # ✅ Get total extra_days from approved leave applications
    extra_days = (
        db.session.query(func.coalesce(func.sum(LeaveApplication.extra_days), 0))
        .filter(
            LeaveApplication.admin_id == admin_id,
            extract('year', LeaveApplication.start_date) == year,
            extract('month', LeaveApplication.start_date) == month,
            LeaveApplication.status == 'Approved'
        )
        .scalar()
    )

    # ✅ Base total
    total_days = working_days - extra_days

    # ✅ Check weekends (till today only)
    first_day = datetime(year, month, 1)
    current_day = first_day
    while current_day <= today:
        if current_day.weekday() in (5, 6):  # 5 = Saturday, 6 = Sunday
            # Check if already punched
            punched = db.session.query(Punch.id).filter(
                Punch.admin_id == admin_id,
                Punch.punch_date == current_day.date(),
                Punch.today_work.isnot(None)
            ).first()

            # Check if on leave
            on_leave = db.session.query(LeaveApplication.id).filter(
                LeaveApplication.admin_id == admin_id,
                LeaveApplication.status == 'Approved',
                LeaveApplication.start_date <= current_day.date(),
                LeaveApplication.end_date >= current_day.date()
            ).first()

            if not punched and not on_leave:
                total_days += 1

        current_day += timedelta(days=1)

    return max(total_days, 0)
  # avoid negative values




# utils/tally.py (recommended place)
import re

def clean_text(text):
    """Remove invalid XML characters from a string."""
    if not text:
        return ""
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', str(text))

# def build_tally_xml(employees, company_name, period_start="20250901", period_end="20250930"):
#     attendance_entries = ""
#     for emp in employees:
#         print(emp)
#         # Clean data to avoid XML exceptions
#         emp_name = clean_text(emp.get('name'))
#         emp_id = clean_text(emp.get('emp_id'))
#         working_days = emp.get('working_days', 0)
#         attendance_entries += f"""
#         <ATTENDANCEENTRIES.LIST>
#             <EMPLOYEENAME>{emp_name}</EMPLOYEENAME>
#             <EMPLOYEENUMBER>{emp_id}</EMPLOYEENUMBER>
#             <ATTENDANCETYPE>Total Present Days</ATTENDANCETYPE>
#             <VALUE>{int(working_days)}</VALUE>
#         </ATTENDANCEENTRIES.LIST>
#         """

#     xml_payload = f"""
#     <ENVELOPE>
#         <HEADER>
#             <TALLYREQUEST>Import Data</TALLYREQUEST>
#         </HEADER>
#         <BODY>
#             <IMPORTDATA>
#                 <REQUESTDESC>
#                     <REPORTNAME>Vouchers</REPORTNAME>
#                     <STATICVARIABLES>
#                         <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
#                     </STATICVARIABLES>
#                 </REQUESTDESC>
#                 <REQUESTDATA>
#                     <TALLYMESSAGE xmlns:UDF="TallyUDF">
#                         <VOUCHER VCHTYPE="Attendance" ACTION="Create">
#                             <DATE>{period_start}</DATE>
#                             <EFFECTIVEDATE>{period_end}</EFFECTIVEDATE>
#                             <VOUCHERTYPENAME>Attendance</VOUCHERTYPENAME>
#                             <NARRATION>Attendance pushed from HRMS</NARRATION>
#                             {attendance_entries}
#                         </VOUCHER>
#                     </TALLYMESSAGE>
#                 </REQUESTDATA>
#             </IMPORTDATA>
#         </BODY>
#     </ENVELOPE>
#     """
#     return clean_text(xml_payload).strip()


def build_tally_xml(employees, company_name, period_start="20250901", period_end="20250930"):
    """
    Build a Tally-compliant XML payload for Attendance vouchers.
    Creates one voucher per employee to ensure Tally recognizes the date.
    """
    from datetime import datetime

    vouchers_xml = ""

    for emp in employees:
        emp_name = clean_text(emp.get('name'))
        emp_id = clean_text(emp.get('emp_id'))
        working_days = emp.get('working_days', 0)

        # Use period_end as the voucher date to match the period
        voucher_number = f"ATT-{period_end}-{emp_id}"  # unique per employee

        attendance_entry = f"""
        <ATTENDANCEENTRIES.LIST>
            <EMPLOYEENAME>{emp_name}</EMPLOYEENAME>
            <EMPLOYEENUMBER>{emp_id}</EMPLOYEENUMBER>
            <ATTENDANCETYPE>Total Present Days</ATTENDANCETYPE>
            <VALUE>{int(working_days)}</VALUE>
        </ATTENDANCEENTRIES.LIST>
        """

        vouchers_xml += f"""
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
            <VOUCHER VCHTYPE="Attendance" ACTION="Create" OBJVIEW="Attendance Voucher View">
                <DATE>{period_end}</DATE>
                <VOUCHERTYPENAME>Attendance</VOUCHERTYPENAME>
                <VOUCHERNUMBER>{voucher_number}</VOUCHERNUMBER>
                <NARRATION>Attendance pushed from HRMS</NARRATION>
                <PERIODBEGIN>{period_start}</PERIODBEGIN>
                <PERIODEND>{period_end}</PERIODEND>
                <ATTENDANCEPERIODBEGIN>{period_start}</ATTENDANCEPERIODBEGIN>
                <ATTENDANCEPERIODEND>{period_end}</ATTENDANCEPERIODEND>
                {attendance_entry}
            </VOUCHER>
        </TALLYMESSAGE>
        """

    xml_payload = f"""
    <ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Import Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>Vouchers</REPORTNAME>
                    <STATICVARIABLES>
                        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                    </STATICVARIABLES>
                </REQUESTDESC>
                <REQUESTDATA>
                    {vouchers_xml}
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>
    """

    return clean_text(xml_payload).strip()

