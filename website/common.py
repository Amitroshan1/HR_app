from flask import flash, current_app
from flask_mail import Message,Mail
import requests
from .auth import refresh_access_token
from .models.Admin_models import Admin




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
                    "contentType": "Text",
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
                    "contentType": "Text",
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





