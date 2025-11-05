from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, DateField, SelectField,
    TextAreaField, BooleanField, SubmitField
)
from wtforms.validators import DataRequired, Email, Length

class BookingForm(FlaskForm):
    # Personal Info
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[DataRequired()])
    current_address = StringField("Current Address", validators=[DataRequired()])

    # Move-in Info (replaces lease_start_date)
    move_in_date = DateField("Preferred Move-in Date", validators=[DataRequired()])
    lease_term = SelectField("Lease Term", choices=[
        ("6 months", "6 Months"),
        ("12 months", "12 Months")
    ])

    # Additional Info
    special_requests = TextAreaField("Special Requests")

    occupants_count = IntegerField("Number of Occupants", validators=[DataRequired()])
    pets = SelectField("Pets", choices=[("Yes", "Yes"), ("No", "No")])

    emergency_contact_name = StringField("Emergency Contact Name", validators=[DataRequired()])
    emergency_contact_phone = StringField("Emergency Contact Phone", validators=[DataRequired()])
    emergency_contact_relationship = StringField("Relationship", validators=[DataRequired()])

    # Payment
    payment_method = SelectField("Payment Method", choices=[
        ("MPESA", "MPESA"),
        ("Bank Transfer", "Bank Transfer")
    ])

    agree_terms = BooleanField("I agree to the Terms and Conditions", validators=[DataRequired()])

    submit = SubmitField("Submit Booking Request")
