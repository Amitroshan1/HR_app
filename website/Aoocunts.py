from flask import *
from flask_login import login_required,current_user
from .forms.search_from import SearchForm,DetailForm
from .forms.manager import PaySlipForm
from .models.news_feed import PaySlip
import os
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
from .utility import attend_calc
from zoneinfo import ZoneInfo
import calendar
from io import BytesIO
import pandas as pd

Accounts = Blueprint('Accounts', __name__)



@Accounts.route('/Acc_dashbord',methods=['GET','POST'])
@login_required
def Acc_dashbord():
    queries = Query.query.all()
    return render_template('Accounts/Acc_dashboard.html', queries=queries)
 
@Accounts.route('/Acc_search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        circle = form.circle.data
        emp_type = form.emp_type.data

        # Query Signup model based on circle and emp_type
        signups = Signup.query.filter_by(circle=circle, emp_type=emp_type).all()

        if not signups:
            flash('No matching entries found', category='error')
            return redirect(url_for('Accounts.search'))

        # Get email addresses from Signup model
        emails = [signup.email for signup in signups]
        emp_map = {i.email: i.emp_id for i in signups}

        # Query Admin model based on email addresses
        admins = Admin.query.filter(Admin.email.in_(emails)).all()


        if not admins:
            flash('No matching entries found in Admin records', category='error')
            return redirect(url_for('Accounts.search'))

        session['admin_emails'] = emails
        session['circle'] = circle
        session['emp_type'] = emp_type
        session['emp_id_map'] = emp_map

        return redirect(url_for('Accounts.search_results'))

    return render_template('Accounts/search_form.html', form=form)


@Accounts.route('/Acc_search_results', methods=['GET'])
@login_required
def search_results():
    if 'admin_emails' not in session:
        flash('Session expired. Please search again.', category='error')
        return redirect(url_for('Accounts.search'))

    emails = session['admin_emails']
    circle = session['circle']
    emp_type = session['emp_type']
    # Retrieve Admin details based on email
    admins = Admin.query.filter(Admin.email.in_(emails)).all()
    data = [i.id for i in admins]
   
    return render_template(
        'Accounts/search_result.html', 
        admins=admins, 
        circle=circle, 
        emp_type=emp_type
    )


@Accounts.route('/download_excel_acc', methods=['GET'])
@login_required
def download_excel_acc():
    # ✅ Check for session data
    emails = session.get('admin_emails')
    circle = session.get('circle')
    emp_type = session.get('emp_type')
    emp_id_map = session.get('emp_id_map', {})

    if not emails:
        flash('Session expired. Please search again.', category='error')
        return redirect(url_for('Accounts.search'))

    # ✅ Fetch matching admins
    admins = Admin.query.filter(Admin.email.in_(emails)).all()

    # ✅ Get IST current year/month and total days in month
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    year, month = ist_now.year, ist_now.month
    num_days = calendar.monthrange(year, month)[1]

    # ✅ Prepare attendance records
    records = []
    for admin in admins:
        result = attend_calc(year, month, num_days, admin.id) or {
            "attendance": 0,
            "work from home": 0
        }

        records.append({
            'Employee ID': emp_id_map.get(admin.email, 'N/A'),
            'Name': admin.first_name,
            'Month': f"{year}-{month:02d}",
            'Circle': circle,
            'Employee Type': emp_type,
            'Total Present Days': result['attendance']
        })

    # ✅ Convert records to Excel
    output = BytesIO()
    df = pd.DataFrame(records)
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')
    output.seek(0)

    # ✅ Send Excel file to download
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
        print("==== INSIDE POST ====")
        print("Request method:", request.method)
        print("Form validated?", form.validate_on_submit())
        print("Form errors:", form.errors)
        print("Form data:", form.data)

        file = request.files.get('payslip_file')
        print("Uploaded file object:", file)
        print("Uploaded file name:", file.filename if file else "No file uploaded")

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
    return render_template('accounts/add_payslip.html', form=form, employee=employee)

    









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
    photo_filename = None  # ✅ Initialize this at the top

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
            print(f"Is creator: {is_creator}")  # Debugging line

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


    



# attendance_circle_emp_type_6june25.excel