import os
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


smtp_server = "email-smtp.us-east-1.amazonaws.com"
port = 587  # For starttls
sender_email = "first-basket@oddunicycle.com"
password = "BM/1EBA/FAFqfp7rGDyLdqnHWOs2AhVUiDbpjc65dpUn"


def send_mail(recipients, subject, html):

    if recipients and len(recipients):

        for i, recipient in enumerate(recipients):

            if i > 0:
                time.sleep(2)

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = sender_email
            message["To"] = recipient

            message.attach(MIMEText(html, "plain"))
            message.attach(MIMEText(html, "html"))


            try:
                with smtplib.SMTP_SSL(smtp_server, 465) as server:
                    server.login('ses-smtp-user.20231120-154256', password)
                    server.sendmail(sender_email, recipient, message.as_string())
            except Exception as e:
                print(e.message)
                break

html_msg = """
<html><head><style>
    table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
</style></head><body><h1>NEW</h1><br><table style="border:1px solid black;border-collapse:collapse;"><tr><th>event</th><th>team</th><th>player</th><th>current_best_odds</th><th>current_fair_odds</th><th>current_ev</th></tr><tr><td>1120</td><td>MIN</td><td>Mike Conley</td><td>1400</td><td>1975.52746079058</td><td>-0.27729214460566987</td></tr></table><br><br></body>
"""

send_mail(['levi.delissa@gmail.com'], 'first basket test', html_msg)
