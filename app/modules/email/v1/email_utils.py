"""
Email utility functions for various events in the healthcare system.
Centralizes email sending logic for patient signup, doctor creation,
hospital creation, appointment booking, and appointment changes.
"""

from html import escape

from app.modules.email.v1.mailgun_service import MailgunGateway


async def send_patient_signup_email(
    *,
    service: MailgunGateway,
    patient_name: str,
    patient_email: str,
) -> None:
    """Send welcome email to newly registered patient."""
    safe_name = escape(patient_name)
    await service.send_html_email(
        to=[patient_email],
        subject="Welcome to Arogya Sewa - Patient Registration Confirmed",
        html=(
            f"<p>Hello {safe_name},</p>"
            "<p>Thank you for registering on Arogya Sewa!</p>"
            "<p>Your patient account has been successfully created. "
            "You can now sign in to your account and book appointments with doctors.</p>"
            "<p><strong>Key features:</strong></p>"
            "<ul>"
            "<li>Browse available doctors and specialists</li>"
            "<li>Book appointments at your convenience</li>"
            "<li>View your appointment history</li>"
            "<li>Manage your health records</li>"
            "</ul>"
            "<p>If you have any questions or face any issues, please contact our support team.</p>"
            "<p>Welcome aboard!</p>"
            "<p>Best regards,<br>Arogya Sewa Team</p>"
        ),
        text_fallback=(
            f"Hello {patient_name},\n\n"
            "Thank you for registering on Arogya Sewa!\n\n"
            "Your patient account has been successfully created. "
            "You can now sign in to your account and book appointments with doctors.\n\n"
            "Key features:\n"
            "- Browse available doctors and specialists\n"
            "- Book appointments at your convenience\n"
            "- View your appointment history\n"
            "- Manage your health records\n\n"
            "If you have any questions or face any issues, please contact our support team.\n\n"
            "Welcome aboard!\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )


async def send_password_reset_otp_email(
    *,
    service: MailgunGateway,
    recipient_email: str,
    otp_code: str,
) -> None:
    """Send password reset OTP email."""
    await service.send_html_email(
        to=[recipient_email],
        subject="Password Reset OTP",
        html=(
            "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; "
            "padding: 20px; background-color: #f9f9f9;'>"
            "<div style='background-color: white; padding: 30px; border-radius: 10px; "
            "box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>"
            "<h2 style='color: #333; text-align: center; margin-bottom: 20px;'>"
            "Password Reset Request</h2>"
            "<p style='color: #666; font-size: 16px; line-height: 1.5;'>Hello,</p>"
            "<p style='color: #666; font-size: 16px; line-height: 1.5;'>"
            "You have requested to reset your password. Please use the following OTP code:</p>"
            "<div style='text-align: center; margin: 30px 0;'>"
            f"<span style='background-color: #007bff; color: white; padding: 15px 30px; "
            f"border-radius: 5px; font-size: 24px; font-weight: bold; letter-spacing: 3px;'>{otp_code}</span>"
            "</div>"
            "<p style='color: #666; font-size: 14px; line-height: 1.5;'>"
            "This OTP will expire in 2 minutes.</p>"
            "<p style='color: #999; font-size: 12px; margin-top: 30px;'>"
            "If you did not request this, please ignore this email.</p>"
            "</div>"
            "<div style='text-align: center; margin-top: 20px;'>"
            "<p style='color: #666; font-size: 14px; line-height: 1.5;'>Thank you!</p>"
            "</div>"
            "</div>"
        ),
        text_fallback=(
            "Password Reset Request\n\n"
            f"Your OTP for password reset is: {otp_code}\n"
            "This OTP will expire in 2 minutes.\n\n"
            "If you did not request this, please ignore this email."
        ),
    )


async def send_doctor_creation_email(
    *,
    service: MailgunGateway,
    doctor_name: str,
    doctor_email: str,
    department: str | None = None,
    hospital_name: str | None = None,
) -> None:
    """Send account creation email to newly created doctor."""
    safe_doctor_name = escape(doctor_name)
    safe_department = escape(department) if department else None
    safe_hospital_name = escape(hospital_name) if hospital_name else None
    department_info_html = f" in {safe_department}" if safe_department else ""
    hospital_info_html = f" at {safe_hospital_name}" if safe_hospital_name else ""
    department_info = f" in {department}" if department else ""
    hospital_info = f" at {hospital_name}" if hospital_name else ""

    await service.send_html_email(
        to=[doctor_email],
        subject="Your Doctor Account on Arogya Sewa has been Created",
        html=(
            f"<p>Hello Dr. {safe_doctor_name},</p>"
            "<p>Welcome to Arogya Sewa!</p>"
            f"<p>Your doctor account has been successfully created{department_info_html}{hospital_info_html}.</p>"
            "<p>You can now sign in to your account and:</p>"
            "<ul>"
            "<li>Manage your appointment schedule</li>"
            "<li>Set your availability slots</li>"
            "<li>View patient appointments</li>"
            "<li>Track appointment history</li>"
            "</ul>"
            "<p>Please complete your profile and update any additional information if needed.</p>"
            "<p>If you have any questions, please contact the hospital administration.</p>"
            "<p>Best regards,<br>Arogya Sewa Team</p>"
        ),
        text_fallback=(
            f"Hello Dr. {doctor_name},\n\n"
            "Welcome to Arogya Sewa!\n\n"
            f"Your doctor account has been successfully created{department_info}{hospital_info}.\n\n"
            "You can now sign in to your account and:\n"
            "- Manage your appointment schedule\n"
            "- Set your availability slots\n"
            "- View patient appointments\n"
            "- Track appointment history\n\n"
            "Please complete your profile and update any additional information if needed.\n\n"
            "If you have any questions, please contact the hospital administration.\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )


async def send_hospital_creation_email(
    *,
    service: MailgunGateway,
    admin_name: str,
    admin_email: str,
    hospital_name: str,
    hospital_location: str,
    contact_number: str,
) -> None:
    """Send welcome email to hospital admin with hospital details."""
    safe_admin_name = escape(admin_name)
    safe_hospital_name = escape(hospital_name)
    safe_hospital_location = escape(hospital_location)
    safe_contact_number = escape(contact_number)

    await service.send_html_email(
        to=[admin_email],
        subject="Your Hospital has been Successfully Registered on Arogya Sewa",
        html=(
            f"<p>Hello {safe_admin_name},</p>"
            "<p>Congratulations! Your hospital has been successfully registered on Arogya Sewa.</p>"
            "<p><strong>Hospital Details:</strong></p>"
            "<ul>"
            f"<li>Hospital Name: {safe_hospital_name}</li>"
            f"<li>Location: {safe_hospital_location}</li>"
            f"<li>Contact Number: {safe_contact_number}</li>"
            "</ul>"
            "<p>As the hospital administrator, you can now:</p>"
            "<ul>"
            "<li>Add and manage doctors</li>"
            "<li>Create and manage departments</li>"
            "<li>View all appointments</li>"
            "<li>Track payment information</li>"
            "<li>Manage hospital information</li>"
            "</ul>"
            "<p>Please log in to your account to complete your hospital setup and add doctors.</p>"
            "<p>If you need any assistance, please contact our support team.</p>"
            "<p>Best regards,<br>Arogya Sewa Team</p>"
        ),
        text_fallback=(
            f"Hello {admin_name},\n\n"
            "Congratulations! Your hospital has been successfully registered on Arogya Sewa.\n\n"
            "Hospital Details:\n"
            f"- Hospital Name: {hospital_name}\n"
            f"- Location: {hospital_location}\n"
            f"- Contact Number: {contact_number}\n\n"
            "As the hospital administrator, you can now:\n"
            "- Add and manage doctors\n"
            "- Create and manage departments\n"
            "- View all appointments\n"
            "- Track payment information\n"
            "- Manage hospital information\n\n"
            "Please log in to your account to complete your hospital setup and add doctors.\n\n"
            "If you need any assistance, please contact our support team.\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )


async def send_appointment_booked_email(
    *,
    service: MailgunGateway,
    recipient_name: str,
    recipient_email: str,
    recipient_type: str,  # "patient", "doctor", or "hospital_admin"
    patient_name: str,
    doctor_name: str,
    hospital_name: str,
    appointment_date: str,
    appointment_time: str,
    appointment_id: str,
) -> None:
    """Send appointment booked notification to patient, doctor, and hospital admin."""
    if recipient_type == "patient":
        subject = "Appointment Booked Successfully"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nYour appointment has been successfully booked!\n\n"
            "Appointment Details:\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Please arrive at least 10 minutes before your appointment time.\n"
            "If you need to reschedule or cancel, please log into your account.\n"
        )
    elif recipient_type == "doctor":
        subject = "New Appointment Scheduled"
        opening = f"Hello Dr. {recipient_name},"
        body = (
            f"\nA new appointment has been scheduled for you.\n\n"
            "Appointment Details:\n"
            f"- Patient: {patient_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Please log into your account to view the full patient details and appointment information.\n"
        )
    else:  # hospital_admin
        subject = "New Appointment Booked at Your Hospital"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nA new appointment has been booked at your hospital.\n\n"
            "Appointment Details:\n"
            f"- Patient: {patient_name}\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Please log into your admin panel to view all appointment details.\n"
        )

    await service.send_html_email(
        to=[recipient_email],
        subject=subject,
        html=(
            f"<p>{escape(opening)}</p>"
            f"<p>{escape(body).replace(chr(10), '<br>')}</p>"
            "<p>If you have any questions, please contact our support team.</p>"
            "<p>Best regards,<br>Arogya Sewa Team</p>"
        ),
        text_fallback=(
            f"{opening}\n\n"
            f"{body}"
            "If you have any questions, please contact our support team.\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )


async def send_appointment_payment_confirmed_email(
    *,
    service: MailgunGateway,
    recipient_name: str,
    recipient_email: str,
    recipient_type: str,  # "patient", "doctor", or "hospital_admin"
    patient_name: str,
    doctor_name: str,
    hospital_name: str,
    appointment_date: str,
    appointment_time: str,
    appointment_id: str,
    paid_amount: float,
    remaining_due: float | None = None,
) -> None:
    """Send payment confirmation email for appointment."""
    if recipient_type == "patient":
        subject = "Appointment Payment Confirmed"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nYour payment for the appointment has been confirmed!\n\n"
            "Appointment Details:\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Payment Information:\n"
            f"- Amount Paid: Rs. {paid_amount:.2f}\n"
        )
        if remaining_due and remaining_due > 0:
            body += f"- Remaining Amount Due: Rs. {remaining_due:.2f}\n"
        else:
            body += "- Full payment completed!\n"
        body += (
            "\nPlease arrive at least 10 minutes before your appointment time.\n"
            "Your appointment is confirmed and ready.\n"
        )
    elif recipient_type == "doctor":
        subject = "Appointment Payment Confirmed"
        opening = f"Hello Dr. {recipient_name},"
        body = (
            f"\nPayment has been confirmed for your scheduled appointment.\n\n"
            "Appointment Details:\n"
            f"- Patient: {patient_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Payment Information:\n"
            f"- Amount Received: Rs. {paid_amount:.2f}\n"
        )
        if remaining_due and remaining_due > 0:
            body += f"- Remaining Amount Due: Rs. {remaining_due:.2f}\n"
        else:
            body += "- Full payment completed!\n"
        body += "\nThe appointment is confirmed and ready to proceed.\n"
    else:  # hospital_admin
        subject = "Appointment Payment Confirmed"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nPayment has been confirmed for an appointment at your hospital.\n\n"
            "Appointment Details:\n"
            f"- Patient: {patient_name}\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Date: {appointment_date}\n"
            f"- Time: {appointment_time}\n"
            f"- Appointment ID: {appointment_id}\n\n"
            "Payment Information:\n"
            f"- Amount Received: Rs. {paid_amount:.2f}\n"
        )
        if remaining_due and remaining_due > 0:
            body += f"- Remaining Amount Due: Rs. {remaining_due:.2f}\n"
        else:
            body += "- Full payment completed!\n"
        body += "\nPlease log into your admin panel for complete payment details.\n"

    await service.send_html_email(
        to=[recipient_email],
        subject=subject,
        html=(
            f"<p>{escape(opening)}</p>"
            f"<p>{escape(body).replace(chr(10), '<br>')}</p>"
            "<p>If you have any questions, please contact our support team.</p>"
            "<p>Best regards,<br>Arogya Sewa Team</p>"
        ),
        text_fallback=(
            f"{opening}\n\n"
            f"{body}"
            "If you have any questions, please contact our support team.\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )


async def send_appointment_time_changed_email(
    *,
    service: MailgunGateway,
    recipient_name: str,
    recipient_email: str,
    recipient_type: str,  # "patient", "doctor", or "hospital_admin"
    patient_name: str,
    doctor_name: str,
    hospital_name: str,
    old_appointment_date: str,
    old_appointment_time: str,
    new_appointment_date: str,
    new_appointment_time: str,
    appointment_id: str,
    change_reason: str | None = None,
) -> None:
    """Send appointment time change notification to patient, doctor, and hospital admin."""
    if recipient_type == "patient":
        subject = "Your Appointment Time has been Changed"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nYour appointment has been rescheduled to a new time.\n\n"
            "Previous Appointment Time:\n"
            f"- Date: {old_appointment_date}\n"
            f"- Time: {old_appointment_time}\n\n"
            "New Appointment Time:\n"
            f"- Date: {new_appointment_date}\n"
            f"- Time: {new_appointment_time}\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Appointment ID: {appointment_id}\n\n"
        )
        if change_reason:
            body += f"Reason for Change: {change_reason}\n\n"
        body += "Please update your schedule accordingly. Please arrive at least 10 minutes before the new appointment time.\n"
    elif recipient_type == "doctor":
        subject = "Appointment Time has been Changed"
        opening = f"Hello Dr. {recipient_name},"
        body = (
            f"\nOne of your scheduled appointments has been rescheduled.\n\n"
            "Previous Appointment Time:\n"
            f"- Date: {old_appointment_date}\n"
            f"- Time: {old_appointment_time}\n\n"
            "New Appointment Time:\n"
            f"- Date: {new_appointment_date}\n"
            f"- Time: {new_appointment_time}\n"
            f"- Patient: {patient_name}\n"
            f"- Hospital: {hospital_name}\n"
            f"- Appointment ID: {appointment_id}\n\n"
        )
        if change_reason:
            body += f"Reason for Change: {change_reason}\n\n"
        body += "Please update your schedule accordingly.\n"
    else:  # hospital_admin
        subject = "Appointment Time Changed at Your Hospital"
        opening = f"Hello {recipient_name},"
        body = (
            f"\nAn appointment has been rescheduled at your hospital.\n\n"
            "Previous Appointment Time:\n"
            f"- Date: {old_appointment_date}\n"
            f"- Time: {old_appointment_time}\n\n"
            "New Appointment Time:\n"
            f"- Date: {new_appointment_date}\n"
            f"- Time: {new_appointment_time}\n"
            f"- Patient: {patient_name}\n"
            f"- Doctor: Dr. {doctor_name}\n"
            f"- Appointment ID: {appointment_id}\n\n"
        )
        if change_reason:
            body += f"Reason for Change: {change_reason}\n\n"
        body += "Please log into your admin panel for complete details.\n"

    await service.send_text_email(
        to=[recipient_email],
        subject=subject,
        text=(
            f"{opening}\n\n"
            f"{body}"
            "If you have any questions, please contact our support team.\n\n"
            "Best regards,\n"
            "Arogya Sewa Team"
        ),
    )
