from flask import flash, current_app,url_for
from flask_mail import Message,Mail
import requests
from flask_login import current_user
from .auth import refresh_access_token
from .models.Admin_models import Admin
from geopy.distance import geodesic

from .models.expense import ExpenseClaimHeader  # adjust path if needed
  # wherever you defined this



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
        flash(f"Error: {str(e)}", 'error')
        return False



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
        flash(f"Error: {str(e)}", 'error')
        return False





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
            approve_url = url_for('manager_bp.approve_line_item', item_id=item.id, _external=True)
            reject_url = url_for('manager_bp.reject_line_item', item_id=item.id, _external=True)

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
                    <a href="{approve_url}" style="padding: 6px 12px; background-color: #28a745; color: white; text-decoration: none; border-radius: 4px;">Approve</a>
                    &nbsp;
                    <a href="{reject_url}" style="padding: 6px 12px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 4px;">Reject</a>
                </div>
                <hr>
            """

        body = f"""
        <html>
        <body>
            <p><strong>An expense claim has been submitted.</strong></p>

            <p>
                <strong>Employee:</strong> {header.employee_name}<br>
                <strong>Employee ID:</strong> {header.emp_id}<br>
                <strong>Designation:</strong> {header.designation}<br>
                <strong>Project:</strong> {header.project_name}<br>
                <strong>Country/State:</strong> {header.country_state}<br>
                <strong>Travel Dates:</strong> {header.travel_from_date} to {header.travel_to_date}
            </p>

            <p><strong>Expense Details:</strong></p>
            {line_items_html}
        </body>
        </html>
        """

        recipient_email = "akumar4@saffotech.com"
        cc_emails = ["singhroshan968@gmail.com"]

        return verify_oauth2_and_send_email(header.email, subject, body, recipient_email, cc_emails)

    except Exception as e:
        print(f"[Email Error] Failed to send claim email: {e}")
        return False
