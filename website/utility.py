from io import BytesIO

import pandas as pd
from flask import current_app
from flask_login import current_user

from .common import verify_oauth2_and_send_email
from .models.attendance import Punch, LeaveBalance, LeaveApplication
from .models.Admin_models import Admin
from .models.confirmation_request import ConfirmationRequest
from .models.manager_model import ManagerContact
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





def check_and_send_confirmation_emails():
    """
    ✅ Checks all employees who have completed 6 months since Date of Joining (doj)
    and triggers an email notification to all (L1, L2, L3) managers
    with HR in CC, using Microsoft Graph OAuth2.
    Also creates a ConfirmationRequest record for each employee once.
    """

    # 🚀 Step 0: Start of job
    current_app.logger.info("🚀 Starting check_and_send_confirmation_emails job...")

    today = date.today()
    six_months_ago = today - timedelta(days=180)
    current_app.logger.info(f"📅 Today's date: {today}, 6 months ago: {six_months_ago}")

    # ✅ Step 1: Find employees who completed 6 months and not yet sent confirmation email
    eligible_employees = Signup.query.filter(
        Signup.doj <= six_months_ago,
        Signup.confirmation_email_sent == False
    ).all()

    current_app.logger.info(f"✅ Found {len(eligible_employees)} eligible employees for confirmation check.")

    if not eligible_employees:
        current_app.logger.info("ℹ️ No employees found who completed 6 months.")
        db.session.close()
        return

    for emp in eligible_employees:
        current_app.logger.info(f"🔍 Processing employee: {emp.first_name} ({emp.email}), DOJ={emp.doj}")

        try:
            # ✅ Step 2: Fetch manager contact details
            manager_contact = ManagerContact.query.filter_by(
                circle_name=emp.circle,
                user_type=emp.emp_type
            ).first()

            if not manager_contact:
                current_app.logger.warning(
                    f"⚠️ No manager contact found for {emp.email} in {emp.circle}/{emp.emp_type}."
                )
                continue

            # ✅ Step 3: Collect manager emails (L1, L2, L3)
            to_emails = [
                email for email in [
                    manager_contact.l1_email,
                    manager_contact.l2_email,
                    manager_contact.l3_email
                ] if email
            ]

            current_app.logger.info(f"📨 Manager emails found: {to_emails}")

            if not to_emails:
                current_app.logger.warning(f"⚠️ No valid manager emails for {emp.email}")
                continue

            # ✅ Step 4: HR CC email (fixed)
            hr_cc_email = "hr@company.com"

            # ✅ Step 5: OAuth sender (L2 manager)
            manager_admin = Admin.query.filter_by(email=manager_contact.l2_email).first()

            if not manager_admin:
                current_app.logger.warning(
                    f"⚠️ L2 Manager {manager_contact.l2_email} not found in Admin table."
                )
                continue

            if not manager_admin.oauth_refresh_token:
                current_app.logger.warning(
                    f"⚠️ L2 Manager {manager_contact.l2_email} has no OAuth token. Email skipped for {emp.email}"
                )
                continue

            # ✅ Step 6: Prepare email content
            subject = f"⚡ Confirmation Due: {emp.first_name} ({emp.emp_id})"
            body = f"""
            <p>Dear Team,</p>
            <p>This is an automated reminder that <strong>{emp.first_name}</strong> 
            (<a href="mailto:{emp.email}">{emp.email}</a>) has now completed 
            <strong>6 months</strong> with the organization.</p>
            <p><strong>Date of Joining:</strong> {emp.doj.strftime('%d %B %Y')}</p>
            <p>Please review and confirm their employment status via the HRMS portal.</p>
            <br>
            <p>Regards,<br><strong>HR System</strong></p>
            """

            # ✅ Step 7: Send email to all managers with HR in CC
            email_sent_successfully = False
            for recipient_email in to_emails:
                current_app.logger.info(f"📤 Sending email to {recipient_email} (CC: {hr_cc_email}) for {emp.email}...")

                success = verify_oauth2_and_send_email(
                    user=manager_admin,
                    subject=subject,
                    body=body,
                    recipient_email=recipient_email,
                    cc_emails=[hr_cc_email]
                )

                if success:
                    email_sent_successfully = True
                    current_app.logger.info(
                        f"✅ Successfully sent to {recipient_email} (cc: {hr_cc_email}) for {emp.email}"
                    )
                else:
                    current_app.logger.warning(
                        f"⚠️ Failed to send email to {recipient_email} for {emp.email}"
                    )

            # ✅ Step 8: Create a ConfirmationRequest record (only once)
            if email_sent_successfully:
                existing_request = ConfirmationRequest.query.filter_by(employee_id=emp.id).first()
                if not existing_request:
                    new_request = ConfirmationRequest(
                        employee_id=emp.id,
                        l1_email=manager_contact.l1_email,
                        l2_email=manager_contact.l2_email,
                        l3_email=manager_contact.l3_email,
                        status='Pending'
                    )
                    db.session.add(new_request)
                    current_app.logger.info(f"📝 ConfirmationRequest created for {emp.email}")

                # ✅ Step 9: Mark confirmation email as sent
                emp.confirmation_email_sent = True
                db.session.commit()
                current_app.logger.info(f"✅ Updated confirmation_email_sent=True for {emp.email}")

        except Exception as e:
            current_app.logger.error(f"💥 Error processing {emp.email}: {e}")
            db.session.rollback()

    # ✅ Step 10: Clean up session
    db.session.close()
    current_app.logger.info("🏁 Finished check_and_send_confirmation_emails job.")


from datetime import datetime, date, timedelta
import calendar
from .models.attendance import Punch, LeaveApplication

def calculate_month_summary(admin_id, year, month):
    """Returns complete monthly summary:
       - Working hours Mon–Fri
       - Working hours Mon–Sat
       - Leaves + Extra days
       - Expected hours
       - Accurate working_days_final using punch + leave logic (month based)
    """

    # -------------------------------------------------------
    # SAFE MONTH (avoid crashes)
    # -------------------------------------------------------
    try:
        num_days = calendar.monthrange(year, month)[1]
    except:
        today = datetime.today()
        year, month = today.year, today.month
        num_days = calendar.monthrange(year, month)[1]

    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    # -------------------------------------------------------
    # FETCH PUNCHES FOR THE MONTH
    # -------------------------------------------------------
    punches = Punch.query.filter(
        Punch.admin_id == admin_id,
        Punch.punch_date >= month_start,
        Punch.punch_date <= month_end
    ).all()

    actual_fri_seconds = 0
    actual_sat_seconds = 0

    # Helper to calculate time difference
    def calc_work(p_in, p_out):
        if not p_in or not p_out:
            return 0
        d_in = datetime.combine(date.min, p_in)
        d_out = datetime.combine(date.min, p_out)
        if d_out < d_in:
            d_out += timedelta(days=1)
        return int((d_out - d_in).total_seconds())

    # -------------------------------------------------------
    # TOTAL WORKED HOURS
    # -------------------------------------------------------
    for p in punches:
        # Prefer today_work if available
        if getattr(p, "today_work", None):
            tw = p.today_work
            secs = tw.hour*3600 + tw.minute*60 + getattr(tw, "second", 0)
        else:
            secs = calc_work(p.punch_in, p.punch_out)

        weekday = p.punch_date.weekday()   # 0=Mon ... 6=Sun

        if weekday not in (5, 6):   # Mon–Fri
            actual_fri_seconds += secs

        if weekday != 6:            # Mon–Sat
            actual_sat_seconds += secs

    # -------------------------------------------------------
    # LEAVES & EXTRA DAYS
    # -------------------------------------------------------
    leave_days = 0
    extra_days = 0

    leaves = LeaveApplication.query.filter(
        LeaveApplication.admin_id == admin_id,
        LeaveApplication.status == "Approved",
        LeaveApplication.start_date <= month_end,
        LeaveApplication.end_date >= month_start
    ).all()

    for lv in leaves:

        # Overlap handling
        ls = max(lv.start_date, month_start)
        le = min(lv.end_date, month_end)

        if le >= ls:
            leave_days += (le - ls).days + 1

        # Extra days
        if getattr(lv, "extra_days", None):
            try:
                ed = float(lv.extra_days)
                if ed > 0:
                    extra_days += ed
            except:
                pass

    # -------------------------------------------------------
    # ADVANCED WORKING DAYS LOGIC (from your bulk function)
    # -------------------------------------------------------

    # Get admin profile to extract emp_type
    admin_obj = Admin.query.get(admin_id)
    signup = Signup.query.filter_by(email=admin_obj.email).first()
    emp_type = getattr(signup, "emp_type", "")

    working_days = 0.0

    # Loop through each day of the selected month
    for d in range(1, num_days + 1):

        the_day = date(year, month, d)
        weekday = the_day.weekday()

        is_weekend = weekday in (5, 6)
        is_sunday = weekday == 6

        # ---- CHECK PUNCHES FOR THAT DAY ----
        punch = next((p for p in punches if p.punch_date == the_day), None)

        punch_value = 0
        if punch:
            in_present = bool(punch.punch_in)
            out_present = bool(punch.punch_out)

            if in_present and out_present:
                punch_value = 1
            elif in_present or out_present:
                punch_value = 0.5

        # ---- CHECK LEAVE FOR THE DAY ----
        leave_for_day = False
        for lv in leaves:
            if lv.start_date <= the_day <= lv.end_date:
                leave_for_day = True
                break

        # ---- APPLY SAME RULES AS BULK FUNCTION ----
        if emp_type in ("Engineering", "Software Development"):
            # Sat + Sun always counted as working
            if is_weekend:
                working_days += 1
            elif punch_value > 0 or leave_for_day:
                working_days += punch_value if punch_value > 0 else 1

        else:  # Accounts, HR, etc.
            if is_sunday:
                working_days += 1
            elif weekday == 5:  # Saturday
                if punch_value > 0 or leave_for_day:
                    working_days += punch_value if punch_value > 0 else 1
            else:  # Mon–Fri
                if punch_value > 0 or leave_for_day:
                    working_days += punch_value if punch_value > 0 else 1

    # Subtract extra days
    working_days -= extra_days
    if working_days < 0:
        working_days = 0

    # Round clean
    working_days_final = round(working_days, 1)

    # -------------------------------------------------------
    # CALENDAR WORKING DAYS (for expected hours only)
    # -------------------------------------------------------
    total_mon_fri = sum(1 for d in range(1, num_days + 1)
                        if date(year, month, d).weekday() not in (5, 6))

    total_mon_sat = sum(1 for d in range(1, num_days + 1)
                        if date(year, month, d).weekday() != 6)

    # -------------------------------------------------------
    # RETURN FINAL SUMMARY
    # -------------------------------------------------------
    return {
        "actual_fri_hours": round(actual_fri_seconds / 3600, 1),
        "actual_sat_hours": round(actual_sat_seconds / 3600, 1),
        "expected_fri_hours": round(total_mon_fri * 8.5, 1),
        "expected_sat_hours": round(total_mon_sat * 8.5, 1),
        "leave_days": leave_days,
        "extra_days": extra_days,
        "working_days_final": working_days_final,
    }

# -------- HOLIDAYS 2026 --------

HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year Day
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 9, 14),  # Ganesh Chaturthi
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 11, 8),  # Diwali
    date(2026, 11, 10), # Govardhan Puja
    date(2025, 12, 25), # Christmas
    date(2026, 11, 11), # Bhaubij
}

OPTIONAL_HOLIDAYS_2026 = {
    date(2026, 3, 19),  # Gudi Padwa
    date(2026, 3, 21),  # Eid # Christmas
}



import xlsxwriter
from zoneinfo import ZoneInfo


from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
from sqlalchemy import func


def calculate_attendance(admin_id, emp_type, year, month):
    # -------- DATE RANGE --------
    start_date = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    end_date = today if (year == today.year and month == today.month) else month_end

    # -------- FETCH PUNCHES --------
    punches = Punch.query.filter(
        Punch.admin_id == admin_id,
        Punch.punch_date.between(start_date, end_date)
    ).all()
    punch_map = {p.punch_date: p for p in punches}

    # -------- FETCH LEAVES (OVERLAPPING MONTH) --------
    leaves = LeaveApplication.query.filter(
        LeaveApplication.admin_id == admin_id,
        LeaveApplication.start_date <= end_date,
        LeaveApplication.end_date >= start_date
    ).all()

    # Build date → leave_status map
    leave_map = {}
    for leave in leaves:
        d = max(leave.start_date, start_date)
        while d <= min(leave.end_date, end_date):
            leave_map[d] = leave.status
            d += timedelta(days=1)

    # -------- COUNTERS --------
    total_present = 0.0
    total_absent = 0.0

    # -------- DAY-WISE LOOP --------
    current = start_date
    while current <= end_date:
        weekday = current.weekday()  # Mon=0 ... Sun=6
        punch = punch_map.get(current)
        leave_status = leave_map.get(current)

        # ---------- HOLIDAY (AUTO PRESENT) ----------
        if current in HOLIDAYS_2026:
            total_present += 1
            current += timedelta(days=1)
            continue

        # ---------- SUNDAY (AUTO PRESENT) ----------
        if weekday == 6:
            total_present += 1
            current += timedelta(days=1)
            continue

        # ---------- SATURDAY ----------
        # HR & Accounts → working day
        # Others → auto-present
        if weekday == 5 and emp_type not in ["Human Resource", "Accounts"]:
            total_present += 1
            current += timedelta(days=1)
            continue

        # ---------- LEAVE HANDLING (OVERRIDES EVERYTHING) ----------
        if leave_status:
            if leave_status == "Approved":
                total_present += 1
            else:  # Pending / Rejected
                total_absent += 1
            current += timedelta(days=1)
            continue

        # ---------- WORKING DAY (PUNCH REQUIRED) ----------
        if punch and punch.punch_in and punch.punch_out:
            # FULL DAY ONLY (no half-day logic)
            total_present += 1

        else:
            # ❗ THIS FIXES YOUR ISSUE:
            # No punch OR punch-in only → ABSENT
            total_absent += 1

        current += timedelta(days=1)

    # -------- EXTRA DAYS (LEAVE OVERFLOW) --------
    # These days are NOT working days → count as ABSENT
    extra_days = db.session.query(
        func.coalesce(func.sum(LeaveApplication.extra_days), 0)
    ).filter(
        LeaveApplication.admin_id == admin_id,
        LeaveApplication.status == "Approved",
        LeaveApplication.start_date <= end_date,
        LeaveApplication.end_date >= start_date
    ).scalar() or 0

    if extra_days > 0:
        total_present = max(0, total_present - extra_days)
        total_absent += extra_days

    return total_present, total_absent



def get_leave_balance(admin):
    signup = Signup.query.filter_by(email=admin.email).first()
    if not signup:
        return 0, 0

    balance = LeaveBalance.query.filter_by(signup_id=signup.id).first()
    if not balance:
        return 0, 0

    return (
        balance.privilege_leave_balance or 0,
        balance.casual_leave_balance or 0
    )



from io import BytesIO
import calendar
import xlsxwriter
from sqlalchemy import func


def generate_attendance_excel(admins, emp_type, circle, year, month):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Attendance")

    # -------- FORMATS --------
    header_fmt = workbook.add_format({
        'bold': True,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#D9E1F2'
    })
    cell_fmt = workbook.add_format({'border': 1})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 12})

    # -------- HEADER --------
    worksheet.merge_range('A1:M1', f"Employee Domain: {emp_type}", title_fmt)
    worksheet.merge_range('A2:M2', f"Circle: {circle}", title_fmt)
    worksheet.merge_range('A3:M3', f"Month: {calendar.month_name[month]} {year}", title_fmt)

    # -------- TABLE HEADER --------
    row = 4
    headers = [
        "S.No",
        "Month",
        "Employee Name",
        "Total Days in Month",
        "Total Working Days(CL+PL)",
        "Total Absent Days",
        "Balance CL",
        "Balance PL",
        "Balance Comp Off",
        "Applied CL",
        "Applied PL",
        "Total Applied Leave"
    ]

    for col, h in enumerate(headers):
        worksheet.write(row, col, h, header_fmt)

    # -------- DATE RANGE FOR MONTH --------
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    # -------- DATA --------
    row += 1
    for idx, admin in enumerate(admins, start=1):

        # Employee name
        signup = Signup.query.filter_by(email=admin.email).first()
        emp_name = signup.first_name if signup else admin.first_name

        # Attendance (SOURCE OF TRUTH)
        present, absent = calculate_attendance(admin.id, emp_type, year, month)

        # Total days in month
        total_days = calendar.monthrange(year, month)[1]

        # Leave balances
        balance = LeaveBalance.query.filter_by(signup_id=signup.id).first() if signup else None
        balance_cl = balance.casual_leave_balance if balance else 0
        balance_pl = balance.privilege_leave_balance if balance else 0
        balance_comp = balance.compensatory_leave_balance if balance else 0

        # Optional holiday balance (adjust if you store differently)

        # -------- APPLIED LEAVES (MONTH-WISE) --------
        applied_cl = db.session.query(func.coalesce(func.sum(LeaveApplication.deducted_days), 0)).filter(
            LeaveApplication.admin_id == admin.id,
            LeaveApplication.leave_type == "Casual Leave",
            LeaveApplication.start_date <= month_end,
            LeaveApplication.end_date >= month_start
        ).scalar() or 0

        applied_pl = db.session.query(func.coalesce(func.sum(LeaveApplication.deducted_days), 0)).filter(
            LeaveApplication.admin_id == admin.id,
            LeaveApplication.leave_type == "Privilege Leave",
            LeaveApplication.start_date <= month_end,
            LeaveApplication.end_date >= month_start
        ).scalar() or 0


        total_applied_leave = applied_cl + applied_pl

        # -------- WRITE ROW --------
        worksheet.write_row(row, 0, [
            idx,
            f"{calendar.month_name[month]} {year}",
            emp_name,
            total_days,
            present,
            absent,                # 🔥 FROM calculate_attendance
            balance_cl,
            balance_pl,
            balance_comp,
            applied_cl,
            applied_pl,
            total_applied_leave
        ], cell_fmt)

        row += 1

    worksheet.set_column(0, 11, 22)
    workbook.close()
    output.seek(0)

    return output


from datetime import datetime, timedelta, time

def calculate_total_work(punch_in, punch_out):
    """Return total work duration as a time object (HH:MM:SS)."""
    if not punch_in or not punch_out:
        return None

    # Combine with dummy date to calculate timedelta
    in_dt = datetime.combine(datetime.min, punch_in)
    out_dt = datetime.combine(datetime.min, punch_out)

    # Handle overnight shift (punch out next day)
    if out_dt < in_dt:
        out_dt += timedelta(days=1)

    work_duration = out_dt - in_dt  # timedelta

    # Convert timedelta → time (HH:MM:SS)
    total_seconds = int(work_duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return time(hour=hours % 24, minute=minutes, second=seconds)



from datetime import datetime, date, timedelta
import calendar
from .models.attendance import Punch, LeaveApplication

def calculate_month_summary_HR(admin_id, year, month):
    """Returns complete monthly summary:
       - Working hours Mon–Fri
       - Working hours Mon–Sat
       - Leaves + Extra days
       - Expected hours
       - Accurate working_days_final using punch + leave logic (month based)
    """

    # -------------------------------------------------------
    # SAFE MONTH (avoid crashes)
    # -------------------------------------------------------
    try:
        num_days = calendar.monthrange(year, month)[1]
    except:
        today = datetime.today()
        year, month = today.year, today.month
        num_days = calendar.monthrange(year, month)[1]

    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    # -------------------------------------------------------
    # FETCH PUNCHES FOR THE MONTH
    # -------------------------------------------------------
    punches = Punch.query.filter(
        Punch.admin_id == admin_id,
        Punch.punch_date >= month_start,
        Punch.punch_date <= month_end
    ).all()

    actual_fri_seconds = 0
    actual_sat_seconds = 0

    # Helper to calculate time difference
    def calc_work(p_in, p_out):
        if not p_in or not p_out:
            return 0
        d_in = datetime.combine(date.min, p_in)
        d_out = datetime.combine(date.min, p_out)
        if d_out < d_in:
            d_out += timedelta(days=1)
        return int((d_out - d_in).total_seconds())

    # -------------------------------------------------------
    # TOTAL WORKED HOURS
    # -------------------------------------------------------
    for p in punches:
        # Prefer today_work if available
        if getattr(p, "today_work", None):
            tw = p.today_work
            secs = tw.hour*3600 + tw.minute*60 + getattr(tw, "second", 0)
        else:
            secs = calc_work(p.punch_in, p.punch_out)

        weekday = p.punch_date.weekday()   # 0=Mon ... 6=Sun

        if weekday not in (5, 6):   # Mon–Fri
            actual_fri_seconds += secs

        if weekday != 6:            # Mon–Sat
            actual_sat_seconds += secs

    # -------------------------------------------------------
    # LEAVES & EXTRA DAYS
    # -------------------------------------------------------
    leave_days = 0
    extra_days = 0

    leaves = LeaveApplication.query.filter(
        LeaveApplication.admin_id == admin_id,
        LeaveApplication.status == "Approved",
        LeaveApplication.start_date <= month_end,
        LeaveApplication.end_date >= month_start
    ).all()

    for lv in leaves:

        # Overlap handling
        ls = max(lv.start_date, month_start)
        le = min(lv.end_date, month_end)

        if le >= ls:
            leave_days += (le - ls).days + 1

        # Extra days
        if getattr(lv, "extra_days", None):
            try:
                ed = float(lv.extra_days)
                if ed > 0:
                    extra_days += ed
            except:
                pass

    # -------------------------------------------------------
    # ADVANCED WORKING DAYS LOGIC (from your bulk function)
    # -------------------------------------------------------

    # Get admin profile to extract emp_type
    admin_obj = Admin.query.get(admin_id)
    signup = Signup.query.filter_by(email=admin_obj.email).first()
    emp_type = getattr(signup, "emp_type", "")

    working_days = 0.0

    # Loop through each day of the selected month
    for d in range(1, num_days + 1):

        the_day = date(year, month, d)
        weekday = the_day.weekday()

        is_weekend = weekday in (5, 6)
        is_sunday = weekday == 6

        # ---- CHECK PUNCHES FOR THAT DAY ----
        punch = next((p for p in punches if p.punch_date == the_day), None)

        punch_value = 0
        if punch:
            in_present = bool(punch.punch_in)
            out_present = bool(punch.punch_out)

            if in_present and out_present:
                punch_value = 1
            elif in_present or out_present:
                punch_value = 0.5

        # ---- CHECK LEAVE FOR THE DAY ----
        leave_for_day = False
        for lv in leaves:
            if lv.start_date <= the_day <= lv.end_date:
                leave_for_day = True
                break

        # ---- APPLY SAME RULES AS BULK FUNCTION ----
        if emp_type in ("Engineering", "Software Development"):
            # Sat + Sun always counted as working
            if is_weekend:
                working_days += 1
            elif punch_value > 0 or leave_for_day:
                working_days += punch_value if punch_value > 0 else 1

        else:  # Accounts, HR, etc.
            if is_sunday:
                working_days += 1
            elif weekday == 5:  # Saturday
                if punch_value > 0 or leave_for_day:
                    working_days += punch_value if punch_value > 0 else 1
            else:  # Mon–Fri
                if punch_value > 0 or leave_for_day:
                    working_days += punch_value if punch_value > 0 else 1

    # Subtract extra days
    working_days -= extra_days
    if working_days < 0:
        working_days = 0

    # Round clean
    working_days_final = round(working_days, 1)

    # -------------------------------------------------------
    # CALENDAR WORKING DAYS (for expected hours only)
    # -------------------------------------------------------
    total_mon_fri = sum(1 for d in range(1, num_days + 1)
                        if date(year, month, d).weekday() not in (5, 6))

    total_mon_sat = sum(1 for d in range(1, num_days + 1)
                        if date(year, month, d).weekday() != 6)

    # -------------------------------------------------------
    # RETURN FINAL SUMMARY
    # -------------------------------------------------------
    return {
        "actual_fri_hours": round(actual_fri_seconds / 3600, 1),
        "actual_sat_hours": round(actual_sat_seconds / 3600, 1),
        "expected_fri_hours": round(total_mon_fri * 8.5, 1),
        "expected_sat_hours": round(total_mon_sat * 8.5, 1),
        "leave_days": leave_days,
        "extra_days": extra_days,
        "working_days_final": working_days_final,
    }





def generate_attendance_excel_HR(admins, emp_type, circle, year, month, file_prefix):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        workbook = writer.book
        worksheet = workbook.add_worksheet("Attendance")
        writer.sheets["Attendance"] = worksheet

        # Styles
        border_fmt = workbook.add_format({'border': 1})
        header_fmt = workbook.add_format({'border': 1, 'bold': True, 'align': 'center',
                                          'valign': 'vcenter', 'bg_color': '#D9E1F2'})
        absent_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFD966'})
        bold_fmt = workbook.add_format({'bold': True})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 12})

        # Summary Colors
        orange_fmt = workbook.add_format({'border': 1, 'bg_color': '#F4B183', 'bold': True})
        green_fmt  = workbook.add_format({'border': 1, 'bg_color': '#C6EFCE', 'bold': True})
        red_fmt    = workbook.add_format({'border': 1, 'bg_color': '#F8CBAD', 'bold': True})
        blue_fmt   = workbook.add_format({'border': 1, 'bg_color': '#BDD7EE', 'bold': True})

        # Dates
        num_days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        # Header Info
        worksheet.write(0, 0, "emp_type", bold_fmt)
        worksheet.write(0, 1, emp_type)
        worksheet.write(0, 3, "Circle", bold_fmt)
        worksheet.write(0, 4, circle)
        worksheet.write(0, 6, "Month", bold_fmt)
        worksheet.write(0, 7, f"{calendar.month_name[month]} {year}", title_fmt)

        # Day labels
        days = [f"{d} {calendar.day_abbr[date(year, month, d).weekday()][0]}"
                for d in range(1, num_days + 1)]

        # Fetch punches
        punches = Punch.query.filter(
            Punch.admin_id.in_([a.id for a in admins]),
            Punch.punch_date >= start_date,
            Punch.punch_date <= end_date
        ).all()

        punch_map = {}
        for p in punches:
            punch_map.setdefault(p.admin_id, {})[p.punch_date.day] = p

        # Fetch emp IDs
        emails = [a.email for a in admins]
        signup = Signup.query.filter(Signup.email.in_(emails)).all()

        # emp_id from signup
        emp_ids = {s.email: s.emp_id for s in signup}

        # full name comes from signup.first_name column
        emp_names = {s.email: s.first_name for s in signup}

        # Start writing
        row = 2
        for admin in admins:

            emp_code = emp_ids.get(admin.email, "N/A")

            worksheet.write(row, 0, "Emp ID:", bold_fmt)
            worksheet.write(row, 1, emp_code)
            worksheet.write(row, 3, "Emp Name:", bold_fmt)
            emp_name = emp_names.get(admin.email, admin.first_name)
            worksheet.write(row, 4, emp_name)
            row += 1

            # Punch rows
            in_times = []
            out_times = []
            totals = []

            admin_punches = punch_map.get(admin.id, {})

            for d in range(1, num_days + 1):
                punch = admin_punches.get(d)

                if punch:
                    in_t = punch.punch_in.strftime("%I:%M %p") if punch.punch_in else ""
                    out_t = punch.punch_out.strftime("%I:%M %p") if punch.punch_out else ""

                    in_times.append(in_t)
                    out_times.append(out_t)

                    # Work hours
                    total_text = ""
                    if punch.today_work:
                        tw = punch.today_work
                        secs = tw.hour * 3600 + tw.minute * 60 + getattr(tw, "second", 0)
                        if secs > 0:
                            h, rem = divmod(secs, 3600)
                            m, _ = divmod(rem, 60)
                            total_text = f"{h} hrs {m} min"

                    if not total_text and punch.punch_in and punch.punch_out:
                        d_in = datetime.combine(date.min, punch.punch_in)
                        d_out = datetime.combine(date.min, punch.punch_out)
                        secs = (d_out - d_in).total_seconds()
                        if secs < 0:
                            secs += 86400
                        h, rem = divmod(int(secs), 3600)
                        m, _ = divmod(rem, 60)
                        total_text = f"{h} hrs {m} min"

                    totals.append(total_text)
                else:
                    in_times.append("")
                    out_times.append("")
                    totals.append("")

            # Write day header
            worksheet.write(row, 0, "Days", header_fmt)
            for col, dval in enumerate(days, start=1):
                worksheet.write(row, col, dval, header_fmt)
            row += 1

            # Write rows
            for label, data in [("InTime", in_times),
                                ("OutTime", out_times),
                                ("Total", totals)]:
                worksheet.write(row, 0, label, header_fmt)
                for col, val in enumerate(data, start=1):
                    fmt = absent_fmt if not val else border_fmt
                    worksheet.write(row, col, val, fmt)
                row += 1

            row += 1

            # SUMMARY
            stats = calculate_month_summary_HR(admin.id, year, month)
            mlabel = f"{calendar.month_name[month]} {year}"

            worksheet.write(row, 0, f"Total Working Days ({mlabel}):", orange_fmt)
            worksheet.write(row, 1, stats["working_days_final"], orange_fmt)
            row += 1

            worksheet.write(row, 0, "Total Approved Leaves (days):", green_fmt)
            worksheet.write(row, 1, stats["leave_days"], green_fmt)
            row += 1

            worksheet.write(row, 0, "Extra Days (non-working):", red_fmt)
            worksheet.write(row, 1, stats["extra_days"], red_fmt)
            row += 1

            worksheet.write(row, 0, f"Total Working Hours ({mlabel}) excluding Saturday :", blue_fmt)
            worksheet.write(row, 1,
                            f'{stats["actual_fri_hours"]} hrs (Expected: {stats["expected_fri_hours"]} hrs)',
                            blue_fmt)
            row += 1

            worksheet.write(row, 0, f"Total Working Hours ({mlabel}) including Saturday :", blue_fmt)
            worksheet.write(row, 1,
                            f'{stats["actual_sat_hours"]} hrs (Expected: {stats["expected_sat_hours"]} hrs)',
                            blue_fmt)
            row += 2

        worksheet.set_column(0, num_days + 1, 18)

    output.seek(0)
    return output
