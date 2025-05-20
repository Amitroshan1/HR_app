
from flask import Blueprint,request, jsonify
from flask import current_app
from datetime import datetime, timedelta,timezone
import requests
from website.models.Admin_models import Admin
from website import db
from flask_jwt_extended import decode_token

from website.models.Admin_models import Admin


auth_helper = Blueprint('auth_helper', __name__)

# Inside website/utils/oauth_helpers.py


def refresh_access_token(admin):
    """Refresh OAuth2 access token using the stored refresh token."""
    if not admin.oauth_refresh_token:
        return None

    refresh_data = {
        "client_id": current_app.config["OAUTH2_CLIENT_ID"],
        "client_secret": current_app.config["OAUTH2_CLIENT_SECRET"],
        "refresh_token": admin.oauth_refresh_token,
        "grant_type": "refresh_token"
    }

    response = requests.post(current_app.config["MICROSOFT_TOKEN_URL"], data=refresh_data)
    new_token_data = response.json()

    if "access_token" not in new_token_data:
        return None

    # Update user record with new tokens
    admin.oauth_token = new_token_data["access_token"]
    admin.oauth_refresh_token = new_token_data.get("refresh_token", admin.oauth_refresh_token)
    admin.oauth_token_expiry = datetime.now() + timedelta(seconds=new_token_data.get("expires_in", 3600))
    db.session.commit()

    return admin.oauth_token





# Microsoft's Public Keys URL for JWT verification
MICROSOFT_JWKS_URL = "https://login.microsoftonline.com/common/discovery/keys"

def fetch_microsoft_keys():
    """ Fetch Microsoft's public keys for validating JWT """
    response = requests.get(MICROSOFT_JWKS_URL)
    return response.json() if response.status_code == 200 else None

@auth_helper.route("/get-current-user", methods=["GET"])
def get_current_user():
    """ Fetch the current authenticated user's email using OAuth2 Access Token """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    access_token = auth_header.split(" ")[1]

    # Decode JWT token (validate with Microsoft)
    try:
        keys = fetch_microsoft_keys()
        decoded_token = decode_token(access_token, algorithms=["RS256"], key=keys)  
    except Exception as e:
        return jsonify({"error": "Invalid token", "details": str(e)}), 401

    # Extract Microsoft ID and email
    microsoft_id = decoded_token.get("sub")
    email = decoded_token.get("email")

    if not microsoft_id:
        return jsonify({"error": "Invalid token, missing user ID"}), 401

    # Fetch user from the database
    user = Admin.query.filter_by(oauth_id=microsoft_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check token expiry and refresh if needed
    if user.oauth_token_expiry and user.oauth_token_expiry < datetime.now(timezone.utc):
        return jsonify({"error": "Access token expired"}), 401

    return jsonify({"email": user.email, "first_name": user.first_name}), 200

