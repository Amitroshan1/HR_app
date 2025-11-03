from flask_login import current_user

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




def get_total_working_days_bulk(admins=None):
    """
    Calculates total working days for each admin from 1st of the current month up to today.
    Considers punches, leaves, weekends, emp_type rules, and extra leave days.
    """

    today = datetime.today()
    year, month = today.year, today.month

    # --- Use current user if no admins passed ---
    if admins is None or len(admins) == 0:
        admins = [current_user]

    # --- Fetch data ---
    admin_ids = [a.id for a in admins]
    admin_emails = [a.email for a in admins]

    # --- Fetch signup details to get emp_type ---
    signups = Signup.query.filter(Signup.email.in_(admin_emails)).all()
    signup_map_by_email = {s.email: getattr(s, 'emp_type', '') for s in signups}

    # --- Fetch punches and leaves for current month ---
    punches = db.session.query(Punch).filter(
        Punch.admin_id.in_(admin_ids),
        extract('year', Punch.punch_date) == year,
        extract('month', Punch.punch_date) == month
    ).all()

    leaves = db.session.query(LeaveApplication).filter(
        LeaveApplication.admin_id.in_(admin_ids),
        LeaveApplication.status == 'Approved',
        extract('year', LeaveApplication.start_date) == year,
        extract('month', LeaveApplication.start_date) == month
    ).all()

    # --- Normalize punch data ---
    punch_map = {}  # {admin_id: {date: [punches...]}}

    for p in punches:
        pd = p.punch_date.date() if isinstance(p.punch_date, datetime) else p.punch_date
        punch_map.setdefault(p.admin_id, {}).setdefault(pd, []).append(p)

    # --- Normalize leave data ---
    leave_map = {}  # {admin_id: [(start_date, end_date, leave_obj)]}

    for l in leaves:
        sdate = l.start_date if isinstance(l.start_date, date) else l.start_date.date()
        edate = l.end_date if isinstance(l.end_date, date) else l.end_date.date()
        leave_map.setdefault(l.admin_id, []).append((sdate, edate, l))

    total_days_map = {}

    # --- Month start and end (till today only) ---
    first_of_month = datetime(year, month, 1).date()
    last_date = today.date()  # 🔹 Only till today, not full month

    # --- Iterate over admins ---
    for admin in admins:
        emp_type = signup_map_by_email.get(admin.email, '')
        total_days = 0.0
        current_day = first_of_month

        while current_day <= last_date:
            weekday = current_day.weekday()  # Monday=0 ... Sunday=6
            is_weekend = weekday in (5, 6)
            is_sunday = weekday == 6

            # Get punch and leave info for this day
            punches_for_day = punch_map.get(admin.id, {}).get(current_day, [])
            leave_for_day = None

            for sdate, edate, lobj in leave_map.get(admin.id, []):
                if sdate <= current_day <= edate:
                    leave_for_day = lobj
                    break

            # Determine punch value
            punch_value = 0
            if punches_for_day:
                p = punches_for_day[0]
                in_present = bool(getattr(p, 'punch_in', None))
                out_present = bool(getattr(p, 'punch_out', None))
                if in_present and out_present:
                    punch_value = 1
                elif in_present or out_present:
                    punch_value = 0.5

            # --- Apply rules ---
            if emp_type in ('Engineering', 'Software Development'):
                # Sat & Sun always counted
                if is_weekend:
                    total_days += 1
                elif punch_value > 0 or leave_for_day:
                    total_days += punch_value if punch_value > 0 else 1

            else:  # Accounts, HR, etc.
                if is_sunday:
                    total_days += 1
                elif weekday == 5:  # Saturday
                    if punch_value > 0 or leave_for_day:
                        total_days += punch_value if punch_value > 0 else 1
                else:  # Monday–Friday
                    if punch_value > 0 or leave_for_day:
                        total_days += punch_value if punch_value > 0 else 1

            # --- Debug print ---
            print(
                f"[DEBUG] admin={admin.id} date={current_day} "
                f"weekday={weekday} punch_value={punch_value} "
                f"leave={'yes' if leave_for_day else 'no'} "
                f"total_so_far={total_days}"
            )

            current_day += timedelta(days=1)

        # --- Adjust with extra_days ---
        leaves_for_admin = leave_map.get(admin.id, [])
        extra_days_total = sum(
            (lobj.extra_days or 0)
            for (sdate, edate, lobj) in leaves_for_admin
            if getattr(lobj, 'status', None) == 'Approved'
        )

        total_days -= extra_days_total
        total_days = max(total_days, 0)
        total_days_map[admin.id] = round(total_days, 1)

        print(f"[DEBUG] ✅ Final total for admin {admin.id}: {total_days_map[admin.id]}")

    return total_days_map








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