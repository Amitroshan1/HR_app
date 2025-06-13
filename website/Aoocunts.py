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

        # Query Admin model based on email addresses
        admins = Admin.query.filter(Admin.email.in_(emails)).all()

        if not admins:
            flash('No matching entries found in Admin records', category='error')
            return redirect(url_for('Accounts.search'))

        session['admin_emails'] = emails
        session['circle'] = circle
        session['emp_type'] = emp_type

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

    return render_template(
        'Accounts/search_result.html', 
        admins=admins, 
        circle=circle, 
        emp_type=emp_type
    )


@Accounts.route('/add_payslip/<int:admin_id>', methods=['GET', 'POST'])
@login_required
def add_payslip(admin_id):
    form = PaySlipForm()
    try:
        # Fetch the employee details
        employee = Admin.query.get_or_404(admin_id)
    except Exception as e:
        flash(f"Error fetching employee details: {e}", 'error')
        return redirect(url_for('Accounts.search_results'))

    if form.validate_on_submit():
        try:
            file_path = None
            filename = None
            # Handle file upload
            if form.payslip_file.data:
                filename = secure_filename(form.payslip_file.data.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                form.payslip_file.data.save(file_path)
        except Exception as e:
            flash(f"Error saving file: {e}", 'error')
            return redirect(url_for('Accounts.add_payslip', admin_id=admin_id))

        try:
            # Create a new PaySlip entry
            new_payslip = PaySlip(
                admin_id=employee.id,
                month=form.month.data,
                year=form.year.data,
                file_path=filename  
            )
            db.session.add(new_payslip)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving PaySlip to the database: {e}", 'error')
            return redirect(url_for('Accounts.add_payslip', admin_id=admin_id))
                
        try:
            # Send email notifica
            email = employee.email
            
            account_email = current_user.email
            
            subject = f'Payslip of Month {form.month.data} Uploaded'
            body = (
                f"Dear {employee.first_name},\n\n"
                f"This mail is to inform you that Payslip for the month {form.month.data} has been generated.\n"
                f"Please find the Payslip in HRMS.\n\n"
                f"Thanks,\nAccounts"
            )

            # Use OAuth2 authentication to send email
            Company_verify_oauth2_and_send_email(account_email, subject, body, email, cc_emails=None)
            flash('PaySlip added successfully! Email has been sent.', 'success')
            return redirect(url_for('Accounts.search_results'))

        except Exception as e:
            flash(f"Error sending email: {e}", 'error')
            return redirect(url_for('Accounts.add_payslip', admin_id=admin_id))

        
    

    return render_template('Accounts/add_payslip.html', form=form, employee=employee)









@Accounts.route('/payslips', methods=['GET'])
@login_required
def view_payslips():
    payslips = PaySlip.query.filter_by(admin_id=current_user.id).order_by(PaySlip.year.desc(), PaySlip.month.desc()).all()

    if not payslips:
        flash('No PaySlips available', 'warning')
        return render_template('Accounts/view_payslips.html', payslips=payslips)  # Redirect to the dashboard or any other relevant page

    return render_template('Accounts/view_payslips.html', payslips=payslips)




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

    if form.validate_on_submit():
        # Create a new query and save it to the database
        new_query = Query(
            admin_id=current_user.id,
            emp_type=', '.join(form.emp_type.data),
            title=form.title.data,
            query_text=form.query_text.data
        )
        db.session.add(new_query)
        db.session.commit()

        # Notify the user that the query has been created
        flash('Your query has been created successfully.', 'success')

        return redirect(url_for('Accounts.create_query'))

    # Display the user's previous queries
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

    
    form = QueryReplyForm()  
    replies = QueryReply.query.filter(QueryReply.query_id == query_id).order_by(QueryReply.created_at.asc()).all()

 
    if form.validate_on_submit():
        reply_text = form.reply_text.data 

        if reply_text:
            new_reply = QueryReply(
                query_id=query_id,
                admin_id=current_user.id,
                reply_text=reply_text
            )
            db.session.add(new_reply)

             # ✅ Set IST time using pytz
            ist = pytz.timezone('Asia/Kolkata')
            ist_time = datetime.now(ist)
            selected_query.created_at = ist_time

            db.session.commit()
            
            return redirect(url_for('Accounts.chat_query', query_id=query_id))

    return render_template('Accounts/chat.html', query=selected_query, replies=replies, form=form,signups_data=signups_data)







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


    



