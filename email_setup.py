"""Email System Setup and Test Script"""

import json
from pathlib import Path
from email_service import test_email_connection, send_alert_email, load_email_config, save_email_config
import pandas as pd


def setup_email_interactive():
	"""Interactive email setup"""
	print("\n" + "="*60)
	print("⚙️  SMART GRID EMAIL SETUP")
	print("="*60 + "\n")
	
	print("📧 Gmail Setup Required:")
	print("-" * 60)
	print("1. Go to: myaccount.google.com/security")
	print("2. Enable '2-Step Verification'")
	print("3. Generate 'App Password' (Mail + Windows)")
	print("4. Copy the 16-character password")
	print("-" * 60 + "\n")
	
	smtp_server = input("SMTP Server [smtp.gmail.com]: ").strip() or "smtp.gmail.com"
	smtp_port = input("SMTP Port [587]: ").strip() or "587"
	sender_email = input("Your Gmail Address: ").strip()
	sender_password = input("App Password (16 chars): ").strip()
	use_tls = input("Use TLS [y/n] [y]: ").strip().lower() != 'n'
	
	if not sender_email or not sender_password:
		print("\n❌ Email and password are required!")
		return False
	
	print("\n⏳ Testing connection...")
	success, message = test_email_connection(sender_email, sender_password, smtp_server, int(smtp_port))
	
	if success:
		print(f"✓ {message}\n")
		
		# Save configuration
		config = {
			"enabled": True,
			"smtp_server": smtp_server,
			"smtp_port": int(smtp_port),
			"sender_email": sender_email,
			"sender_password": sender_password,
			"use_tls": use_tls
		}
		save_email_config(config)
		print("✓ Configuration saved!\n")
		
		# Test email
		print("📨 Sending test email...")
		test_recipient = input("Test recipient email (or press Enter to use sender): ").strip() or sender_email
		
		test_alert = {
			"meter_id": "TEST-001",
			"pattern": "TEST_ALERT",
			"timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
			"risk_score": 0.85,
			"power": 125.5,
			"voltage": 230.0,
			"current": 15.3,
			"explanation": "This is a test alert from Smart Grid Monitoring System"
		}
		
		email_success, email_message = send_alert_email(test_recipient, test_alert)
		
		if email_success:
			print(f"✓ {email_message}")
			print(f"\n✅ EMAIL SYSTEM READY!\n")
			print(f"Check your inbox: {test_recipient}\n")
			return True
		else:
			print(f"❌ {email_message}\n")
			return False
	else:
		print(f"❌ {message}\n")
		return False


def show_current_config():
	"""Show current email configuration"""
	config = load_email_config()
	print("\n" + "="*60)
	print("📧 CURRENT EMAIL CONFIGURATION")
	print("="*60)
	print(f"Enabled: {config.get('enabled', False)}")
	print(f"SMTP Server: {config.get('smtp_server', 'Not set')}")
	print(f"SMTP Port: {config.get('smtp_port', 'Not set')}")
	print(f"Sender Email: {config.get('sender_email', 'Not set')}")
	print(f"TLS Enabled: {config.get('use_tls', False)}")
	print("="*60 + "\n")


def main():
	print("\n🎯 Smart Grid Email System Setup\n")
	
	while True:
		print("Options:")
		print("1. Setup/Configure Email")
		print("2. Show Current Configuration")
		print("3. Test Connection")
		print("4. Send Test Email")
		print("5. Exit")
		
		choice = input("\nSelect option (1-5): ").strip()
		
		if choice == "1":
			setup_email_interactive()
		
		elif choice == "2":
			show_current_config()
		
		elif choice == "3":
			config = load_email_config()
			if not config.get("sender_email"):
				print("❌ Email not configured. Run option 1 first.\n")
			else:
				print("\n⏳ Testing connection...")
				success, message = test_email_connection(
					config.get("sender_email"),
					config.get("sender_password"),
					config.get("smtp_server"),
					config.get("smtp_port")
				)
				print(f"{'✓' if success else '❌'} {message}\n")
		
		elif choice == "4":
			config = load_email_config()
			if not config.get("enabled"):
				print("❌ Email notifications are disabled. Configure first.\n")
			else:
				recipient = input("Send test email to: ").strip() or config.get("sender_email")
				print("\n⏳ Sending test email...")
				
				test_alert = {
					"meter_id": "TEST-MANUAL",
					"pattern": "THEFT_DETECTION",
					"timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
					"risk_score": 0.90,
					"power": 250.0,
					"voltage": 215.0,
					"current": 25.5,
					"explanation": "Manual test alert - Unauthorized consumption detected"
				}
				
				success, message = send_alert_email(recipient, test_alert)
				print(f"{'✓' if success else '❌'} {message}\n")
		
		elif choice == "5":
			print("\n👋 Exiting...\n")
			break
		
		else:
			print("❌ Invalid option. Try again.\n")


if __name__ == "__main__":
	main()
