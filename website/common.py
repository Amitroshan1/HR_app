from flask import flash, current_app,url_for
from flask_mail import Message,Mail
import requests
from flask_login import current_user
from .auth import refresh_access_token
from .models.Admin_models import Admin
from geopy.distance import geodesic
from .models.manager_model import ManagerContact  # adjust path if needed
from .models.expense import ExpenseClaimHeader  # adjust path if needed
  # wherever you defined this
from .models.signup import Signup  # adjust path if needed



def verify_oauth2_and_send_email(user, subject, body, recipient_email, cc_emails=None):
    try:
        # Ensure `user` is a Signup object, not a string (email)
        if isinstance(user, str):
            user = Admin.query.filter_by(email=user).first()
        if not user or not user.oauth_refresh_token:
            flash("Failed to authenticate with Microsoft. Please re-login.", 'error')
            return False

        access_token = refresh_access_token(user)  # Pass user object

        if not access_token:
            flash("Failed to authenticate with Microsoft. Please re-login.", 'error')
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": [{"emailAddress": {"address": recipient_email}}],
                "ccRecipients": [{"emailAddress": {"address": email}} for email in (cc_emails or [])]
            },
            "saveToSentItems": "true"
        }

        response = requests.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers=headers,
            json=email_data
        )

        if response.status_code == 202:
            return True
        else:
            flash(f"Error sending email: {response.json()}", 'error')
            return False

    except Exception as e:
        raise e




def Company_verify_oauth2_and_send_email(user_email, subject, body, recipient_email, cc_emails=None):
    try:
        # Ensure `user_email` belongs to an Admin with OAuth2 tokens
        user = Admin.query.filter_by(email=user_email).first()

        if not user:
            flash(f"User with email {user_email} not found.", 'error')
            return False

        if not user.oauth_refresh_token:
            flash("OAuth refresh token is missing. Please re-login.", 'error')
            return False

        access_token = refresh_access_token(user)  # Ensure we pass a valid user object

        if not access_token:
            flash("Failed to refresh OAuth2 token. Please re-login.", 'error')
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": [{"emailAddress": {"address": recipient_email}}],
                "ccRecipients": [{"emailAddress": {"address": email}} for email in (cc_emails or [])]
            },
            "saveToSentItems": "true"
        }

        response = requests.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers=headers,
            json=email_data
        )

        if response.status_code == 202:
            return True
        else:
            flash(f"Error sending email: {response.json()}", 'error')
            return False

    except Exception as e:
        raise e
        





def asset_email(recipient_email,first_name):
    
    subject = f'New Asset Assigned to You'
    body = (
                f"Dear {first_name},\n\n"
                f"This mail is to inform you that your new asset has been added.\n\n"
                f"Thanks,\nAccounts"
            )
  
    Company_verify_oauth2_and_send_email(current_user.email, subject, body,recipient_email, )
    return True


def update_asset_email(recipient_email,first_name):
    
    subject = f'Your Asset has been Updated'
    body = (
                f"Dear {first_name},\n\n"
                f"This mail is to inform you that your asset has been updated.\n\n"
                f"Thanks,\nAccounts"
            )
    
    Company_verify_oauth2_and_send_email(current_user.email, subject, body,recipient_email, )
    return True




def is_within_allowed_location(user_lat, user_lon, allowed_locations):
    for loc in allowed_locations:
        loc_coords = (loc.latitude, loc.longitude)
        user_coords = (user_lat, user_lon)
        distance = geodesic(loc_coords, user_coords).meters
        if distance <= loc.radius:
            return True
    return False




def send_claim_submission_email(header):
    try:
        subject = f"Expense Claim Submitted: {header.employee_name} ({header.emp_id})"

        # Build line items with file download + approve/reject buttons
        line_items_html = ""
        for item in header.expenses:
            "https://solviotec.com/"

            file_link = (
                f'<a href="{url_for("static", filename="uploads/" + item.Attach_file, _external=True)}" '
                f'target="_blank" style="color: #007bff;">Download File</a>'
                if item.Attach_file else "No attachment"
            )

            line_items_html += f"""
                <p>
                    <strong>{item.sr_no}.</strong> {item.date.strftime('%Y-%m-%d')} | {item.purpose} | {item.amount} {item.currency} |
                    {file_link} | Status: {item.status}
                </p>
                <div style="margin-top: 8px; margin-bottom: 12px;">
                    <a href= https://solviotec.com/ style="padding: 6px 12px; background-color: #28a745; color: white; text-decoration: none; border-radius: 4px;">Approve</a>
                    &nbsp;
                </div>
                <hr>
            """

        body = f"""
        <html>
    <body style="font-family: Arial, sans-serif;">

        <p><strong>An expense claim has been submitted.</strong></p>

        <table style="border-collapse: collapse; width: 100%;" border="1" cellpadding="8">
            
            <tr>
                <td><strong>Employee</strong></td>
                <td>{header.employee_name}</td>
            </tr>
            <tr>
                <td><strong>Employee ID</strong></td>
                <td>{header.emp_id}</td>
            </tr>
            <tr>
                <td><strong>Designation</strong></td>
                <td>{header.designation}</td>
            </tr>
            <tr>
                <td><strong>Project</strong></td>
                <td>{header.project_name}</td>
            </tr>
            <tr>
                <td><strong>Country/State</strong></td>
                <td>{header.country_state}</td>
            </tr>
            <tr>
                <td><strong>Travel Dates</strong></td>
                <td>{header.travel_from_date} to {header.travel_to_date}</td>
            </tr>
        </table>

        <br>
        <p><strong>Expense Details:</strong></p>
        {line_items_html}

    </body>
    </html>
    """


        recipient_email = "akumar4@saffotech.com"
        cc_emails = ["singhroshan968@gmail.com"]

        return verify_oauth2_and_send_email(header.email, subject, body, recipient_email, cc_emails)

    except Exception as e:
        raise e


def send_wfh_approval_email_to_managers(user, wfh):
    """
    Sends an approval request email to the manager(s) for a submitted WFH application.
    If no manager is found, email is still sent to HR without CC.
    """
    hr_mail = "singhroshan968@gmail.com"


    # Get user circle & emp_type from Signup model
    data = Signup.query.filter_by(email=user.email).first()
    if not data:
        flash("Signup record not found for user.", "error")
        return False

    

    # Try to fetch manager contact
    manager_contacts = ManagerContact.query.filter_by(
        circle_name=data.circle,
        user_type=data.emp_type
    ).first()

    # Collect manager emails if found
    if manager_contacts:
        manager_emails = [manager_contacts.l2_email, manager_contacts.l3_email]
        manager_emails = [email for email in manager_emails if email]  # filter out None
    else:
        manager_emails = []
        

    # Prepare email content
    subject = f"WFH Request from {user.first_name} ({user.email})"
    body = f"""
        <p>Hi,</p>

        <p>
            This is to inform you that <strong>{user.first_name}</strong> has submitted a Work From Home (WFH) request.<br>
            Please review the details below and take the necessary action.
        </p>

        <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;" border="1" cellpadding="8">
            
            <tr>
                <td><strong>Employee Name</strong></td>
                <td>{user.first_name}</td>
            </tr>
            <tr>
                <td><strong>Start Date</strong></td>
                <td>{wfh.start_date.strftime('%d-%m-%Y')}</td>
            </tr>
            <tr>
                <td><strong>End Date</strong></td>
                <td>{wfh.end_date.strftime('%d-%m-%Y')}</td>
            </tr>
            <tr>
                <td><strong>Reason</strong></td>
                <td>{wfh.reason.replace('\n', '<br>')}</td>
            </tr>
            <tr>
                <td><strong>Status</strong></td>
                <td><strong>{wfh.status}</strong></td>
            </tr>
        </table>

        <p>Please log in to the HRMS portal to approve or reject this WFH request.</p>
        """

    # Send email
    return verify_oauth2_and_send_email(
        user=user,
        subject=subject,
        body=body,
        recipient_email=hr_mail,
        cc_emails=manager_emails if manager_emails else None
    )




def send_resignation_email(user, resignation,signup_date
                           ,manager=None):
    subject = f"Resignation Submitted by {user.first_name} ({user.email})"
    body = f"""
    <p>Dear Sir/Madam,</p>

    <p>I hope this message finds you well.</p>

    <p>This is to inform you that <strong>{user.first_name} ({user.email})</strong> has submitted a resignation request. Please find the details below:</p>

    <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;" border="1" cellpadding="8">
        
        <tr>
            <td><strong>Employee Name</strong></td>
            <td>{user.first_name}</td>
        </tr>
        <tr>
            <td><strong>Employee ID</strong></td>
            <td>{signup_date.emp_id}</td>
        </tr>
        <tr>
            <td><strong>Date OF Joining</strong></td>
            <td>{signup_date.doj}</td>
        </tr>
        <tr>
            <td><strong>Employee Type</strong></td>
            <td>{signup_date.emp_type}</td>
        </tr>
        <tr>
            <td><strong>Employee Circle</strong></td>
            <td>{signup_date.circle}</td>
        </tr>
        <tr>
            <td><strong>Resignation Date</strong></td>
            <td>{resignation.resignation_date.strftime('%d-%b-%Y')}</td>
        </tr>
        <tr>
            <td><strong>Reason for Resignation</strong></td>
            <td>{resignation.reason.replace('\n', '<br>')}</td>
        </tr>
    </table>

    <p>Please take the necessary steps to initiate the offboarding process at your earliest convenience.</p>

    <p>Thank you for your attention to this matter.</p>

    <br>
    <p>Warm regards,<br>
    {user.first_name}</p>
    """


    # Primary recipient (e.g., HR)
    recipient_email = "singhroshan968@gmail.com"

    # Add L2 and L3 manager emails to CC if available
    cc_emails = []
    if manager:
        if manager.l2_email:
            cc_emails.append(manager.l2_email)
        if manager.l3_email:
            cc_emails.append(manager.l3_email)

    return verify_oauth2_and_send_email(
        user=user,
        subject=subject,
        body=body,
        recipient_email=recipient_email,
        cc_emails=cc_emails
    )



def send_rollback_resignation_email(user, manager=None):
    subject = f"Resignation Rolled Back by {user.first_name} ({user.email})"
    body = f"""
    <p>Dear Sir/Madam,</p>

    <p>I hope this message finds you in good health and spirits.</p>
    <p>I am writing to formally withdraw my resignation submitted earlier. After careful reflection and discussions, I have reconsidered my decision and chosen to continue contributing to the organization.</p>

    <p>I remain committed to my responsibilities and growth within the company and sincerely appreciate the opportunity to continue being a part of the team.</p>
    <p>Please consider this update in the employee records and halt any further offboarding actions if already initiated.</p>

    <p>Thank you for your cooperation.</p>

    <br>
    <p>Warm regards,<br>
    {user.first_name}</p>
    """

    # Primary recipient
    recipient_email = "singhroshan968@gmail.com"

    # CC managers if available
    cc_emails = []
    if manager:
        if manager.l2_email:
            cc_emails.append(manager.l2_email)
        if manager.l3_email:
            cc_emails.append(manager.l3_email)

    return verify_oauth2_and_send_email(
        user=user,
        subject=subject,
        body=body,
        recipient_email=recipient_email,
        cc_emails=cc_emails
    )
