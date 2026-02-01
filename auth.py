"""User Authentication Module for Smart Grid Dashboard"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Tuple

USERS_FILE = Path("artifacts/users.json")


def hash_password(password: str) -> str:
	"""Hash password using SHA-256"""
	return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> Dict:
	"""Load users from JSON file"""
	if USERS_FILE.exists():
		with open(USERS_FILE, "r") as f:
			return json.load(f)
	return {}


def save_users(users: Dict) -> None:
	"""Save users to JSON file"""
	USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
	with open(USERS_FILE, "w") as f:
		json.dump(users, f, indent=2)


def create_default_users() -> None:
	"""Create default admin and operator users"""
	users = load_users()
	
	if not users:
		users = {
			"admin": {
				"password": hash_password("admin123"),
				"role": "admin",
				"name": "Administrator",
				"email": "admin@smartgrid.local",
				"alerts_enabled": True
			},
			"operator": {
				"password": hash_password("operator123"),
				"role": "operator",
				"name": "Grid Operator",
				"email": "operator@smartgrid.local",
				"alerts_enabled": True
			},
			"viewer": {
				"password": hash_password("viewer123"),
				"role": "viewer",
				"name": "Data Viewer",
				"email": "viewer@smartgrid.local",
				"alerts_enabled": False
			}
		}
		save_users(users)


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
	"""
	Authenticate user credentials
	Returns: (success, username, role)
	"""
	users = load_users()
	
	if username not in users:
		return False, None, None
	
	user = users[username]
	password_hash = hash_password(password)
	
	if user["password"] == password_hash:
		return True, username, user.get("role", "viewer")
	
	return False, None, None


def register_user(username: str, password: str, name: str, role: str = "viewer", email: str = "") -> Tuple[bool, str]:
	"""
	Register a new user (admin only)
	Returns: (success, message)
	"""
	users = load_users()
	
	if username in users:
		return False, "Username already exists"
	
	if len(password) < 6:
		return False, "Password must be at least 6 characters"
	
	users[username] = {
		"password": hash_password(password),
		"role": role,
		"name": name,
		"email": email,
		"alerts_enabled": True
	}
	
	save_users(users)
	return True, f"User '{username}' created successfully"


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
	"""Change user password"""
	users = load_users()
	
	if username not in users:
		return False, "User not found"
	
	user = users[username]
	old_hash = hash_password(old_password)
	
	if user["password"] != old_hash:
		return False, "Old password is incorrect"
	
	if len(new_password) < 6:
		return False, "New password must be at least 6 characters"
	
	user["password"] = hash_password(new_password)
	save_users(users)
	return True, "Password changed successfully"


def get_user_info(username: str) -> Optional[Dict]:
	"""Get user information"""
	users = load_users()
	return users.get(username)


def list_all_users() -> Dict:
	"""List all users (admin only)"""
	users = load_users()
	# Don't return passwords
	return {
		username: {
			"name": user.get("name", username),
			"role": user.get("role", "viewer")
		}
		for username, user in users.items()
	}


def delete_user(username: str) -> Tuple[bool, str]:
	"""Delete a user (admin only)"""
	users = load_users()
	
	if username not in users:
		return False, "User not found"
	
	if username == "admin":
		return False, "Cannot delete admin user"
	
	del users[username]
	save_users(users)
	return True, f"User '{username}' deleted successfully"


def update_user_role(username: str, new_role: str) -> Tuple[bool, str]:
	"""Update user role (admin only)"""
	valid_roles = ["admin", "operator", "viewer"]
	
	users = load_users()
	
	if username not in users:
		return False, "User not found"
	
	if new_role not in valid_roles:
		return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
	
	users[username]["role"] = new_role
	save_users(users)
	return True, f"User '{username}' role updated to '{new_role}'"


def update_user_email(username: str, email: str) -> Tuple[bool, str]:
	"""Update user email address"""
	users = load_users()
	
	if username not in users:
		return False, "User not found"
	
	if not email or "@" not in email:
		return False, "Invalid email address"
	
	users[username]["email"] = email
	save_users(users)
	return True, f"Email updated to {email}"


def toggle_user_alerts(username: str) -> Tuple[bool, str]:
	"""Toggle email alerts for user"""
	users = load_users()
	
	if username not in users:
		return False, "User not found"
	
	current_state = users[username].get("alerts_enabled", False)
	users[username]["alerts_enabled"] = not current_state
	save_users(users)
	
	status = "enabled" if not current_state else "disabled"
	return True, f"Alerts {status} for user '{username}'"


# Initialize default users on first run
if not USERS_FILE.exists():
	create_default_users()
