"""Email Notification Service for Smart Grid Alerts"""

import smtplib
import json
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Tuple, List, Optional

CONFIG_FILE = Path("config.json")


def load_email_config() -> dict:
	"""Load email configuration from config.json"""
	if CONFIG_FILE.exists():
		with open(CONFIG_FILE, "r") as f:
			config = json.load(f)
			return config.get("email", {})
	return {
		"enabled": False,
		"smtp_server": "smtp.gmail.com",
		"smtp_port": 587,
		"sender_email": "",
		"sender_password": "",
		"use_tls": True
	}


def save_email_config(config: dict) -> None:
	"""Save email configuration"""
	full_config = {}
	if CONFIG_FILE.exists():
		with open(CONFIG_FILE, "r") as f:
			full_config = json.load(f)
	
	full_config["email"] = config
	
	with open(CONFIG_FILE, "w") as f:
		json.dump(full_config, f, indent=2)


def test_email_connection(sender_email: str, sender_password: str, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587) -> Tuple[bool, str]:
	"""Test email connection"""
	try:
		server = smtplib.SMTP(smtp_server, smtp_port)
		server.starttls()
		server.login(sender_email, sender_password)
		server.quit()
		return True, "✓ Email connection successful!"
	except smtplib.SMTPAuthenticationError:
		return False, "❌ Authentication failed - check email/password"
	except smtplib.SMTPException as e:
		return False, f"❌ SMTP Error: {str(e)}"
	except Exception as e:
		return False, f"❌ Connection failed: {str(e)}"


def send_alert_email(recipient_email: str, alert_data: dict) -> Tuple[bool, str]:
	"""Send email alert for detected anomaly"""
	config = load_email_config()
	
	if not config.get("enabled") or not config.get("sender_email"):
		return False, "Email notifications are not configured"
	
	try:
		msg = MIMEMultipart("alternative")
		msg["Subject"] = f"⚠️ CRITICAL ALERT - {alert_data.get('pattern', 'Anomaly').upper()} DETECTED"
		msg["From"] = config["sender_email"]
		msg["To"] = recipient_email
		
		# Create HTML email template
		html = f"""
		<html>
			<head>
				<style>
					body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
					.container {{ background-color: white; padding: 20px; border-radius: 8px; margin: 20px; }}
					.alert-header {{ background-color: #ff4757; color: white; padding: 15px; border-radius: 5px; font-size: 18px; font-weight: bold; }}
					.alert-body {{ padding: 15px; border-left: 4px solid #ff4757; background-color: #fff5f5; margin-top: 15px; }}
					.detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
					.label {{ font-weight: bold; color: #333; }}
					.value {{ color: #666; }}
					.risk-high {{ background-color: #ff6b6b; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}
					.risk-medium {{ background-color: #ffd93d; color: #333; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}
					.risk-low {{ background-color: #51cf66; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}
					.footer {{ font-size: 12px; color: #999; margin-top: 20px; text-align: center; }}
				</style>
			</head>
			<body>
				<div class="container">
					<div class="alert-header">
						⚠️ CRITICAL ALERT DETECTED
					</div>
					
					<div class="alert-body">
						<h2 style="color: #ff4757; margin-top: 0;">Smart Grid Monitoring System</h2>
						
						<div class="detail-row">
							<span class="label">Meter ID:</span>
							<span class="value"><strong>{alert_data.get('meter_id', 'N/A')}</strong></span>
						</div>
						
						<div class="detail-row">
							<span class="label">Alert Type:</span>
							<span class="value"><strong>{alert_data.get('pattern', 'N/A').upper()}</strong></span>
						</div>
						
						<div class="detail-row">
							<span class="label">Time:</span>
							<span class="value">{alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</span>
						</div>
						
						<div class="detail-row">
							<span class="label">Risk Score:</span>
							<span class="value">
								{get_risk_badge(alert_data.get('risk_score', 0))}
							</span>
						</div>
						
						<div class="detail-row">
							<span class="label">Power Usage:</span>
							<span class="value">{alert_data.get('power', 'N/A')} kW</span>
						</div>
						
						<div class="detail-row">
							<span class="label">Voltage:</span>
							<span class="value">{alert_data.get('voltage', 'N/A')} V</span>
						</div>
						
						<div class="detail-row">
							<span class="label">Current:</span>
							<span class="value">{alert_data.get('current', 'N/A')} A</span>
						</div>
						
						<div class="detail-row">
							<span class="label">Explanation:</span>
							<span class="value" style="font-style: italic;">{alert_data.get('explanation', 'AI detected anomaly')}</span>
						</div>
					</div>
					
					<div class="footer">
						<p>This is an automated alert from Smart Grid Monitoring System</p>
						<p>Do not reply to this email. Please log in to the dashboard for more details.</p>
						<p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
					</div>
				</div>
			</body>
		</html>
		"""
		
		msg.attach(MIMEText(html, "html"))
		
		# Send email
		server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
		if config.get("use_tls"):
			server.starttls()
		server.login(config["sender_email"], config["sender_password"])
		server.sendmail(config["sender_email"], recipient_email, msg.as_string())
		server.quit()
		
		return True, f"✓ Alert email sent to {recipient_email}"
	
	except Exception as e:
		return False, f"❌ Failed to send email: {str(e)}"


def get_risk_badge(risk_score: float) -> str:
	"""Get HTML badge for risk score"""
	if risk_score >= 0.7:
		return f'<span class="risk-high">HIGH: {risk_score:.2f}</span>'
	elif risk_score >= 0.5:
		return f'<span class="risk-medium">MEDIUM: {risk_score:.2f}</span>'
	else:
		return f'<span class="risk-low">LOW: {risk_score:.2f}</span>'


def send_daily_summary(recipient_email: str, summary_data: dict) -> Tuple[bool, str]:
	"""Send daily summary report"""
	config = load_email_config()
	
	if not config.get("enabled") or not config.get("sender_email"):
		return False, "Email notifications are not configured"
	
	try:
		msg = MIMEMultipart("alternative")
		msg["Subject"] = f"📊 Daily Smart Grid Summary - {datetime.now().strftime('%Y-%m-%d')}"
		msg["From"] = config["sender_email"]
		msg["To"] = recipient_email
		
		html = f"""
		<html>
			<head>
				<style>
					body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
					.container {{ background-color: white; padding: 20px; border-radius: 8px; margin: 20px; }}
					.header {{ background: linear-gradient(135deg, #6C5CE7, #00D2D3); color: white; padding: 20px; border-radius: 5px; }}
					.metric {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #6C5CE7; border-radius: 4px; }}
					.metric-value {{ font-size: 24px; font-weight: bold; color: #6C5CE7; }}
					.metric-label {{ color: #666; font-size: 12px; text-transform: uppercase; }}
					.footer {{ font-size: 12px; color: #999; margin-top: 20px; text-align: center; }}
				</style>
			</head>
			<body>
				<div class="container">
					<div class="header">
						<h1 style="margin: 0;">📊 Daily Smart Grid Summary</h1>
						<p style="margin: 5px 0 0 0;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
					</div>
					
					<div class="metric">
						<div class="metric-label">Total Readings</div>
						<div class="metric-value">{summary_data.get('total_readings', 0)}</div>
					</div>
					
					<div class="metric">
						<div class="metric-label">Total Alerts</div>
						<div class="metric-value" style="color: #ff4757;">{summary_data.get('total_alerts', 0)}</div>
					</div>
					
					<div class="metric">
						<div class="metric-label">Alert Percentage</div>
						<div class="metric-value">{summary_data.get('alert_percentage', 0):.1f}%</div>
					</div>
					
					<div class="metric">
						<div class="metric-label">Total Meters Monitored</div>
						<div class="metric-value">{summary_data.get('total_meters', 0)}</div>
					</div>
					
					<div class="metric">
						<div class="metric-label">Critical Alerts (Risk > 0.7)</div>
						<div class="metric-value" style="color: #ff4757;">{summary_data.get('critical_alerts', 0)}</div>
					</div>
					
					<div class="footer">
						<p>This is an automated report from Smart Grid Monitoring System</p>
						<p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
					</div>
				</div>
			</body>
		</html>
		"""
		
		msg.attach(MIMEText(html, "html"))
		
		server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
		if config.get("use_tls"):
			server.starttls()
		server.login(config["sender_email"], config["sender_password"])
		server.sendmail(config["sender_email"], recipient_email, msg.as_string())
		server.quit()
		
		return True, f"✓ Summary email sent to {recipient_email}"
	
	except Exception as e:
		return False, f"❌ Failed to send email: {str(e)}"
