from flask import *
from flask_login import login_required,current_user

from .forms.attendance import PushToTallyForm
from .forms.search_from import SearchForm,DetailForm
from .forms.manager import PaySlipForm,MultiPaySlipForm
from .models.news_feed import PaySlip
import os
from .models.education import UploadDoc
from werkzeug.utils import secure_filename
from .models.Admin_models import Admin
from .models.signup import Signup
from . import db
from .models.query import Query, QueryReply
from .forms.query_form import QueryForm, QueryReplyForm,PasswordForm
from .models.signup import Signup
from .common import verify_oauth2_and_send_email,Company_verify_oauth2_and_send_email
import pytz
from datetime import datetime
from flask import current_app
from .utility import get_total_working_days_bulk,build_tally_xml
from zoneinfo import ZoneInfo
import calendar
from io import BytesIO
import pandas as pd
from datetime import datetime, date
from .models.attendance import Punch


Accounts = Blueprint('Accounts', __name__)



@Accounts.route('/Acc_dashbord', methods=['GET', 'POST'])
@login_required
def Acc_dashboard():
    form = SearchForm() # existing data you already show
    admins = []                   # search results placeholder

    if form.validate_on_submit():
        circle = form.circle.data
        emp_type = form.emp_type.data

        # Query Signup model
        signups = Signup.query.filter_by(circle=circle, emp_type=emp_type).all()

        if not signups:
            flash('No matching entries found', category='error')
        else:
            emails = [signup.email for signup in signups]
            emp_map = {i.email: i.emp_id for i in signups}

            admins = Admin.query.filter(Admin.email.in_(emails)).all()

            if not admins:
                flash('No matching entries found in Admin records', category='error')
            else:
                # Store search context in session if needed
                session['admin_emails'] = emails
                session['circle'] = circle
                session['emp_type'] = emp_type
                session['emp_id_map'] = emp_map
        return redirect(url_for('Accounts.search_results'))
    return render_template(
        'Accounts/search_form.html',
        form=form,
        
        admins=admins   # pass search results
    )





@Accounts.route('/Acc_search_results', methods=['GET'])
@login_required
def search_results():
    form = PushToTallyForm()

    # Session check
    if not session.get('admin_emails'):
        flash('Session expired. Please search again.', category='error')
        return redirect(url_for('Accounts.Acc_dashboard'))

    emails = session['admin_emails']
    circle = session.get('circle', '')
    emp_type = session.get('emp_type', '')

    # Refresh session
    session['admin_emails'] = emails
    session['circle'] = circle
    session['emp_type'] = emp_type
    session.permanent = True

    # Fetch Admin records
    admins = Admin.query.filter(Admin.email.in_(emails)).all()

    # ✅ Get total working days for all admins in bulk
    total_days_map = get_total_working_days_bulk(admins)

    # Prepare admin_data for template
    admin_data = []
    for admin in admins:
        admin_data.append({
            "id": admin.id,
            "name": admin.first_name,
            "email": admin.email,
            "total_days": total_days_map.get(admin.id, 0)
        })

    return render_template(
        'Accounts/search_result.html',
        admin_data=admin_data,
        circle=circle,
        emp_type=emp_type,
        form=form
    )



import re
def clean_xml(xml_str):
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', xml_str)


@Accounts.route('/push_to_tally', methods=['POST'])
@login_required
def push_to_tally():
    form = PushToTallyForm()

    if not form.validate_on_submit():
        flash("Form submission invalid or CSRF token missing.", "error")
        return redirect(url_for('Accounts.search_results'))

    emails = session.get('admin_emails') or request.form.getlist("emails")

    if not emails:
        flash("Session expired or no employees selected. Please search again.", "error")
        return redirect(url_for('Accounts.Acc_dashboard'))

    # Fetch admins and signup data
    admins = Admin.query.filter(Admin.email.in_(emails)).all()
    signups = {s.email: s for s in Signup.query.filter(Signup.email.in_(emails)).all()}

    employees = []
    for admin in admins:
        total_days = get_total_working_days(admin.id)
        signup = signups.get(admin.email)
        if not signup:
            continue
        employees.append({
            "name": admin.first_name,
            "emp_id": signup.emp_id,
            "working_days": total_days
        })

    if not employees:
        flash("No employee data found to push.", "error")
        return redirect(url_for('Accounts.search_results'))

    # Build XML payload (now creates one voucher per employee)
    xml_payload = clean_xml(build_tally_xml(
        employees,
        company_name="Saffo Solution Technology LLP (Payrol)",
        period_start="20250901",
        period_end="20250930"
    ))

    # Send to Tally
    import requests
    try:
        response = requests.post(
            "http://localhost:9000",
            data=xml_payload.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            timeout=100
        )

        # Check response for errors
        if "<LINEERROR>" in response.text or "<CREATED>0</CREATED>" in response.text:
            flash("❌ Error pushing data to Tally. Response: " + response.text, "error")
        else:
            flash("✅ Attendance pushed successfully to Tally!", "success")

    except Exception as e:
        flash(f"⚠️ Could not connect to Tally: {str(e)}", "error")

    return redirect(url_for('Accounts.search_results'))







@Accounts.route('/view_documents/<int:admin_id>', methods=['GET'])
@login_required
def view_documents(admin_id):
    # Find the admin
    admin = Admin.query.get_or_404(admin_id)

    # Get uploaded docs for this admin
    upload_doc = UploadDoc.query.filter_by(admin_id=admin.id).first()

    if not upload_doc:
        flash("No documents uploaded for this employee.", "warning")
        return redirect(url_for("Accounts.search_results"))

    # Pass admin + uploaded doc to template
    return render_template(
        "Accounts/view_documents.html",
        admin=admin,
        upload_doc=upload_doc
    )


@Accounts.route('/download_document/<int:admin_id>/<doc_field>', methods=['GET'])
@login_required
def download_document(admin_id, doc_field):
    # Validate admin
    admin = Admin.query.get_or_404(admin_id)
    upload_doc = UploadDoc.query.filter_by(admin_id=admin.id).first()

    if not upload_doc:
        flash("No documents found.", "error")
        return redirect(url_for("Accounts.view_documents", admin_id=admin.id))

    # Check requested field exists
    if not hasattr(upload_doc, doc_field):
        flash("Invalid document type.", "error")
        return redirect(url_for("Accounts.view_documents", admin_id=admin.id))

    filename = getattr(upload_doc, doc_field)
    if not filename:
        flash("Document not uploaded.", "error")
        return redirect(url_for("Accounts.view_documents", admin_id=admin.id))

    # Serve file
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'uploads'),
        filename,
        as_attachment=True  # set False for inline view
    )



@Accounts.route('/download_excel_acc', methods=['GET'])
@login_required
def download_excel_acc():
    # 1️⃣ Get session data
    emails = session.get('admin_emails')
    circle = session.get('circle')
    emp_type = session.get('emp_type')
    emp_id_map = session.get('emp_id_map', {})

    # 2️⃣ Check if session expired
    if not emails:
        flash('Session expired. Please search again.', category='error')
        return redirect(url_for('Accounts.search'))

    # 3️⃣ Fetch admin objects
    admins = Admin.query.filter(Admin.email.in_(emails)).all()

    # 4️⃣ Get current IST month and year
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    year, month = ist_now.year, ist_now.month
    num_days = calendar.monthrange(year, month)[1]

    # 5️⃣ Prepare Excel output
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Attendance")
        writer.sheets["Attendance"] = worksheet

        # 6️⃣ Define cell styles
        border_fmt = workbook.add_format({'border': 1})
        header_fmt = workbook.add_format({
            'border': 1, 'bold': True, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D9E1F2'
        })
        absent_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFD966'})  # Yellow for missing
        bold_fmt = workbook.add_format({'bold': True})

        # 7️⃣ Write emp_type and circle at top
        worksheet.write(0, 0, "emp_type", bold_fmt)
        worksheet.write(0, 1, emp_type)
        worksheet.write(0, 3, "CIRCLE", bold_fmt)
        worksheet.write(0, 4, circle)

        # 8️⃣ Generate weekday headers (e.g., "1 M", "2 T", ...)
        days = [f"{d} {calendar.day_abbr[date(year, month, d).weekday()][0]}" for d in range(1, num_days + 1)]

        # 9️⃣ Fetch all punches for the month for all admins
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)
        punches = Punch.query.filter(
            Punch.admin_id.in_([a.id for a in admins]),
            Punch.punch_date >= start_date,
            Punch.punch_date <= end_date
        ).all()

        # 🔟 Map punches by admin_id and day
        punch_map_by_admin = {}
        for p in punches:
            punch_map_by_admin.setdefault(p.admin_id, {})[p.punch_date.day] = p

        # 11️⃣ Start writing rows
        row = 2
        for admin in admins:
            emp_code = emp_id_map.get(admin.email, 'N/A')
            emp_name = admin.first_name

            # 12️⃣ Employee info
            worksheet.write(row, 0, "Emp ID:", bold_fmt)
            worksheet.write(row, 1, emp_code)
            worksheet.write(row, 3, "Emp Name:", bold_fmt)
            worksheet.write(row, 4, emp_name)
            row += 1

            # 13️⃣ Get this admin’s punches
            admin_punch_map = punch_map_by_admin.get(admin.id, {})

            # 14️⃣ Prepare InTime, OutTime, Total lists
            in_times, out_times, totals = [], [], []

            for d in range(1, num_days + 1):
                punch = admin_punch_map.get(d)
                if punch:
                    # 🕒 AM/PM format for times (if present)
                    in_time = punch.punch_in.strftime("%I:%M %p") if punch.punch_in else ""
                    out_time = punch.punch_out.strftime("%I:%M %p") if punch.punch_out else ""

                    in_times.append(in_time)
                    out_times.append(out_time)

                    # ⏱ Compute total using today_work if available, else compute from in/out
                    total_text = ""

                    # 1) use today_work if present and non-zero
                    if getattr(punch, "today_work", None):
                        tw = punch.today_work
                        # compute seconds from time object (handles hour/minute/second)
                        tw_seconds = (tw.hour * 3600) + (tw.minute * 60) + getattr(tw, "second", 0)
                        if tw_seconds > 0:
                            th, rem = divmod(tw_seconds, 3600)
                            tm, _ = divmod(rem, 60)
                            if th and tm:
                                total_text = f"{th:02d} hrs {tm:02d} min"
                            elif th:
                                total_text = f"{th:02d} hrs"
                            elif tm:
                                total_text = f"{tm:02d} min"

                    # 2) fallback to punch_in & punch_out if today_work missing/zero
                    if not total_text and punch.punch_in and punch.punch_out:
                        # combine times and compute delta; handle overnight by adding 24h if negative
                        d_in = datetime.combine(date.min, punch.punch_in)
                        d_out = datetime.combine(date.min, punch.punch_out)
                        delta = d_out - d_in
                        total_seconds = int(delta.total_seconds())
                        if total_seconds < 0:
                            # assume punch_out is next day -> add 24h
                            total_seconds += 24 * 3600
                        if total_seconds > 0:
                            th, rem = divmod(total_seconds, 3600)
                            tm, _ = divmod(rem, 60)
                            if th and tm:
                                total_text = f"{th:02d} hrs {tm:02d} min"
                            elif th:
                                total_text = f"{th:02d} hrs"
                            elif tm:
                                total_text = f"{tm:02d} min"

                    # 3) Append empty string if no total_text (so cell shows yellow missing)
                    totals.append(total_text)
                else:
                    # ❌ No punch record for this date
                    in_times.append("")
                    out_times.append("")
                    totals.append("")

            # 15️⃣ Write header row for days
            worksheet.write(row, 0, "Days", header_fmt)
            for col, val in enumerate(days, start=1):
                worksheet.write(row, col, val, header_fmt)
            row += 1

            # 16️⃣ Write InTime, OutTime, Total rows
            for label, data in [("InTime", in_times), ("OutTime", out_times), ("Total", totals)]:
                worksheet.write(row, 0, label, header_fmt)
                for col, val in enumerate(data, start=1):
                    # show derived value; highlight if missing
                    worksheet.write(row, col, val, absent_fmt if not val else border_fmt)
                row += 1

            # 17️⃣ Blank row between employees
            row += 1

        # 18️⃣ Adjust column widths (slightly wider for AM/PM and totals)
        worksheet.set_column(0, num_days + 1, 16)

    # 19️⃣ Return Excel file
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=f'Attendance_{circle}_{emp_type}_{month}_{year}.xlsx',
        as_attachment=True
    )















@Accounts.route('/add_payslip/<int:admin_id>', methods=['GET', 'POST'])
@login_required
def add_payslip(admin_id):
    form = PaySlipForm()



    try:
        employee = Admin.query.get_or_404(admin_id)
    except Exception:
        flash("Employee details not found.", 'error')
        return redirect(url_for('Accounts.search_results'))

    if request.method == 'POST':
        

        file = request.files.get('payslip_file')
        

        file_path = None
        filename = None

        try:
            # Handle optional file upload
            if form.payslip_file.data:
                filename = secure_filename(form.payslip_file.data.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                form.payslip_file.data.save(file_path)

            # Prepare and send email
            email = employee.email
            account_email = current_user.email
            subject = f'Payslip of Month {form.month.data} Uploaded'
            body = f"""
            <html>
            <body>
                <p>Dear <strong>{employee.first_name}</strong>,</p>
                <p>Your payslip for <strong>{form.month.data}</strong> is now available.</p>
                <p>Thanks,<br><strong>Accounts</strong></p>
            </body>
            </html>
            """


            # Save to database
            new_payslip = PaySlip(
                admin_id=employee.id,
                month=form.month.data,
                year=form.year.data,
                file_path=filename
            )
            db.session.add(new_payslip)
            db.session.commit()
            Company_verify_oauth2_and_send_email(account_email, subject, body, email)
            flash('PaySlip added successfully! Email sent.', 'success')
            return redirect(url_for('Accounts.search_results'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error occurred: {str(e)}", 'error')
            return redirect(url_for('Accounts.add_payslip', admin_id=admin_id))

    # ✅ ALWAYS return something, even if form not submitted
    return render_template('Accounts/add_payslip.html', form=form, employee=employee)



@Accounts.route('/upload_payslips', methods=['GET', 'POST'])
@login_required
def upload_payslips():
    form = MultiPaySlipForm()

    if form.validate_on_submit():
        month = form.month.data
        year = form.year.data
        uploaded_files = form.payslip_files.data

        saved_slips = []   # store (admin, file_path, filename) for later email sending

        for file in uploaded_files:
            if not file or file.filename.strip() == "":
                continue

            filename = secure_filename(file.filename)
            employee_name = os.path.splitext(filename)[0]

            # 🔎 Match employee (by email OR first_name)
            admin = Admin.query.filter(
                (Admin.email.ilike(f"%{employee_name}%")) |
                (Admin.first_name.ilike(f"%{employee_name}%"))
            ).first()

            if not admin:
                flash(f"⚠ No match found for {filename}", "error")
                continue

            # 💾 Save file
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # 📝 Add payslip record
            slip = PaySlip(
                admin_id=admin.id,
                month=month,
                year=year,
                file_path=save_path
            )
            db.session.add(slip)
            saved_slips.append((admin, save_path, filename))

        # ✅ Commit all at once
        db.session.commit()

        # 📧 Now send emails
        for admin, save_path, filename in saved_slips:
            try:
                with open(save_path, "rb") as f:
                    import base64
                    attachment = [{
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": filename,
                        "contentBytes": base64.b64encode(f.read()).decode("utf-8")
                    }]

                subject = f"Payslip for {month} {year}"
                body = f"""
                <p>Dear {admin.first_name},</p>
                <p>Please find attached your payslip for <b>{month} {year}</b>.</p>
                <p>Regards,<br>HR Team</p>
                """

                success = verify_oauth2_and_send_email(
                    user=admin,
                    subject=subject,
                    body=body,
                    recipient_email=admin.email,
                    attachments=attachment
                )

                if success:
                    flash(f"✅ Payslip sent to {admin.email}", "success")
                else:
                    flash(f"❌ Failed to send payslip to {admin.email}", "error")

            except Exception as e:
                flash(f"❌ Error sending {filename} to {admin.email}: {str(e)}", "error")

        return redirect(url_for('Accounts.upload_payslips'))

    return render_template('Accounts/upload_payslip.html', form=form)









@Accounts.route('/payslips', methods=['GET'])
@login_required
def view_payslips():
    payslips = PaySlip.query.filter_by(admin_id=current_user.id).order_by(PaySlip.year.desc(), PaySlip.month.desc()).all()

    emp_type = Signup.query.filter_by(email=current_user.email).first().emp_type

    if not payslips:
        flash('No PaySlips available', 'warning')
        return render_template('Accounts/view_payslips.html', payslips=payslips)  # Redirect to the dashboard or any other relevant page

    return render_template('Accounts/view_payslips.html', payslips=payslips,emp_type=emp_type)




@Accounts.route('/download_payslip/<int:payslip_id>', methods=['GET'])
@login_required
def download_payslip(payslip_id):
    payslip = PaySlip.query.get_or_404(payslip_id)


    if payslip.admin_id != current_user.id:
        flash('You are not authorized to download this PaySlip', 'danger')
        return redirect(url_for('Accounts.view_payslips'))

   
    
    file_path = os.path.join('/var/www/HR_app/website/static/uploads', payslip.file_path)




   
    if not os.path.exists(file_path):
        flash('The requested file does not exist.', 'danger')
        return redirect(url_for('Accounts.view_payslips'))
 
    return send_file(file_path, as_attachment=True)


@Accounts.route('/create_query', methods=['GET', 'POST'])
@login_required
def create_query():
    form = QueryForm()
    photo_filename = None

    if form.validate_on_submit():
        if form.photo.data:
            file = form.photo.data
            file_size = request.content_length

            if file_size and file_size > 1048576:
                flash('File size exceeds 100 KB. Please upload a smaller file.', 'warning')
                return redirect(request.url)
            else:
                filename = secure_filename(file.filename)

                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                photo_filename = filename  # ✅ Set it only if file exists

        # ✅ Now it's safe to use photo_filename
        new_query = Query(
            admin_id=current_user.id,
            emp_type=', '.join(form.emp_type.data),
            title=form.title.data,
            query_text=form.query_text.data,
            photo=photo_filename
        )
        db.session.add(new_query)
        db.session.commit()

        flash('Your query has been created successfully.', 'success')
        return redirect(url_for('Accounts.create_query'))

    user_queries = Query.query.filter_by(admin_id=current_user.id).order_by(Query.created_at.desc()).all()

    return render_template('Accounts/create_query.html', form=form, queries=user_queries)



    



@Accounts.route('/query/<int:query_id>/chat', methods=['GET', 'POST'])
@login_required
def chat_query(query_id):
    
    selected_query = Query.query.get_or_404(query_id)

    if selected_query.status == 'New':
        selected_query.status = 'Open'
        db.session.commit()

    current_email = current_user.email
    
    signups_data = Signup.query.filter_by(email=current_email).first()

    # First, get the Admin who created the query
    query_creator = Admin.query.get(selected_query.admin_id)

    # Then, use their email to fetch the Signup record
    emp_type_of_creator = Signup.query.filter_by(email=query_creator.email).first()



    form = QueryReplyForm()  
    form1 = QueryForm()
    replies = QueryReply.query.filter(QueryReply.query_id == query_id).order_by(QueryReply.created_at.asc()).all()

    if form.validate_on_submit():
        reply_text = form.reply_text.data

        if reply_text:
            # Determine if current user is the one who created the query
            is_creator = emp_type_of_creator.emp_type == signups_data.emp_type
            

            # Set user_type accordingly
            user_type = "User" if is_creator else "Team"

            new_reply = QueryReply(
                query_id=query_id,
                admin_id=current_user.id,
                reply_text=reply_text,
                user_type=user_type
            )
            db.session.add(new_reply)

            # Update the query timestamp
            ist = pytz.timezone('Asia/Kolkata')
            ist_time = datetime.now(ist)
            selected_query.created_at = ist_time

            db.session.commit()

            return redirect(url_for('Accounts.chat_query', query_id=query_id))

    return render_template('Accounts/chat.html', query=selected_query, replies=replies, form=form,form1=form1,signups_data=signups_data)







@Accounts.route('/emp_type_queries')
@login_required
def view_emp_type_queries():
    email=current_user.email
    emp = Signup.query.filter_by(email=email).first()
    emp_type = emp.emp_type
    
    
    queries_for_emp_type = Query.query.filter(
        Query.emp_type.ilike(f'%{emp_type}%') 
    ).all()

    
    for query in queries_for_emp_type:
        admin_details = Admin.query.filter_by(id=query.admin_id).first()
        query.admin_details = admin_details

    return render_template('Accounts/view_emp_type_queries.html', queries=queries_for_emp_type,emp=emp)


@Accounts.route('/delete_query/<int:query_id>', methods=['GET'])
@login_required
def close_query(query_id):
    query = Query.query.filter_by(id=query_id).first()
    
    if not query:
        flash('Query not found.', 'error')
        return redirect(url_for('Accounts.create_query'))
    
    replies = QueryReply.query.filter_by(query_id=query_id).all()
    
    # Construct email body
    body_chat = f"Query Title: {query.title}\n"
    body_chat += f"Department: {query.emp_type}\n\n"
    body_chat += "Chat History:\n"

    for reply in replies:
        admin = Admin.query.filter_by(id=reply.admin_id).first()
        body_chat += f"{admin.first_name}: {reply.reply_text} (on {reply.created_at})\n"

    body_chat += "\nIssue resolved. Closing this query."

   # Split the emp_type string into a list
    departments = query.emp_type.split(', ')

    if len(departments) >1:
    # Determine department email and CC
        if 'Human Resource' in departments:
            department_email = 'hr@saffotech.com'
            cc =['accounts@saffotech.com']
        else:
            department_email = 'accounts@saffotech.com'
            cc = ['hr@saffotech.com']
    else:
        if 'Human Resource' in departments:
            department_email = 'hr@saffotech.com'
            cc=None
        else:
            department_email = 'accounts@saffotech.com'


    subject = f"Query Resolved: {query.title}"

    # Send email using OAuth2
    email_sent = verify_oauth2_and_send_email(current_user, subject, body_chat, department_email, cc)

    if email_sent:
        db.session.delete(query)
        db.session.commit()
        flash('Query resolved and deleted successfully. Notification sent to departments.', 'success')
    else:
        flash('Failed to send email. Query was not deleted.', 'error')

    return redirect(url_for('Accounts.create_query'))


# --- depart_close_query ---
@Accounts.route('/delete_depart_query/<int:query_id>/<string:dept>', methods=['GET'])
@login_required
def close_depart_query(query_id, dept):
    print("function is running")
    print(f"got the id {query_id} department {dept}")
    query = Query.query.filter_by(id=query_id).first()

    if not query:
        flash('Query not found you know very well.', 'error')
        return redirect(url_for('Accounts.create_query'))

    replies = QueryReply.query.filter_by(query_id=query_id).all()

    # Construct email body
    body_chat = f"Query Title: {query.title}\n"
    body_chat += f"Departments: {query.emp_type}\n\n"
    body_chat += "Chat History:\n"

    for reply in replies:
        admin = Admin.query.filter_by(id=reply.admin_id).first()
        body_chat += f"{admin.first_name}: {reply.reply_text} (on {reply.created_at})\n"

    body_chat += "\nIssue resolved. Closing this query."

    # Sender = current user
    sender_email = current_user.email
    print(f"got the sender email {sender_email}")

    # Receiver = query creator
    receiver_email = query.admin.email
    print(f"got the receiver email: {receiver_email}")

    # CC handling: if HR is involved, CC Account; if Account is involved, CC HR
    cc = []
    if "Human Resource" in dept:
        cc.append("chauguleshubham390@gmail.com")  # Account email
    elif "Account" in dept:
        cc.append("skchaugule@safotech.com")  # HR email

    print(f"Final CC list: {cc}")

    subject = f"Query Resolved: {query.title}"

    # Send email
    email_sent = verify_oauth2_and_send_email(
        sender_email, subject, body_chat, receiver_email, cc
    )

    if email_sent:
        db.session.delete(query)
        db.session.commit()
        flash('Query resolved and deleted successfully. Notification sent.', 'success')
    else:
        flash('Failed to send email. Query was not deleted.', 'error')

    return redirect(url_for('Accounts.create_query'))



@Accounts.route('/policy_structure', methods=['GET', 'POST'])
@login_required
def policy_structure():
    user_email = current_user.email
    
    signup_data  = Signup.query.filter_by(email=user_email).first()
    return render_template('policy/policy_structure.html',signup_data=signup_data)

@Accounts.route('/service_policy', methods=['GET', 'POST'])
@login_required
def service_policy():
    return render_template('policy/service_policy.html')

@Accounts.route('/leave_policy', methods=['GET', 'POST'])
@login_required
def leave_policy():
    return render_template('policy/leave_policy.html')


@Accounts.route('/travel_policy', methods=['GET', 'POST'])
@login_required
def travel_policy():
    return render_template('policy/travel_policy.html')

@Accounts.route('/domestic_travel', methods=['GET', 'POST'])
@login_required
def domestic_travel():
    return render_template('policy/domestic_travel.html')

@Accounts.route('/international_travel', methods=['GET', 'POST'])
@login_required
def international_travel():
    return render_template('policy/international_travel.html')


