from asyncio import Event
import base64
from datetime import date, date, datetime
from io import BytesIO
import os
from models.models import Document
from flask import Blueprint, current_app, flash, jsonify, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
import pyotp
from models.models import Booking, MaintenanceRequest, Message, House, Notification, Payment, User
from extensions import db
from models.models import Event
from werkzeug.utils import secure_filename
import base64
from .forms import BookingForm
from utils import booking_to_dict
import uuid
from dateutil.relativedelta import relativedelta
import requests
from models.models import MaintenanceRequest, Payment
from models.models import ChatMessage

#from routes.service_routes import requests  # Needed for encoding password for STK push,this can causecircular loop

tenant_bp = Blueprint('tenant', __name__, url_prefix='/tenant')

# Safaricom Daraja sandbox config
DARJA_CONSUMER_KEY = "YOUR_CONSUMER_KEY"
DARJA_CONSUMER_SECRET = "YOUR_CONSUMER_SECRET"
BUSINESS_SHORTCODE = "174379"
PASSKEY = "YOUR_PASSKEY"
CALLBACK_URL = "https://yourdomain.com/tenant/mpesa_callback"  # Update to your real callback URL

def get_mpesa_token():
    """Fetch OAuth token from Safaricom"""
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(auth_url, auth=(DARJA_CONSUMER_KEY, DARJA_CONSUMER_SECRET))
    r.raise_for_status()
    token = r.json().get("access_token")
    return token

def initiate_stk_push(phone_number, amount, account_reference):
    """Initiate STK Push"""
    token = get_mpesa_token()
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": float(amount),
        "PartyA": phone_number,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": "Rent Payment"
    }
    
    r = requests.post(stk_url, json=payload, headers=headers)
    return r.json()

# ---------------- Initiate payment route ----------------
@tenant_bp.route('/pay_rent_mpesa', methods=['POST'])
@login_required
def pay_rent_mpesa():
    phone_number = request.form.get('phone')
    amount = request.form.get('amount')

    if not phone_number or not amount:
        return jsonify({"error": "Phone number and amount are required"}), 400

    account_ref = f"Rent-{current_user.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    response = initiate_stk_push(phone_number, amount, account_ref)

    # Optionally, store a pending payment record
    pending_payment = Payment(
        tenant_id=current_user.id,
        amount=float(amount),
        date=datetime.utcnow(),
        status='Pending'
    )
    db.session.add(pending_payment)
    db.session.commit()

    return jsonify(response)

# ---------------- Callback endpoint ----------------
@tenant_bp.route('/mpesa_callback', methods=['POST'])
def mpesa_callback():
    """Safaricom will POST transaction results here"""
    data = request.get_json()
    try:
        result_code = data['Body']['stkCallback']['ResultCode']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']

        # Find the pending payment in DB
        payment = Payment.query.filter_by(status='Pending').order_by(Payment.date.desc()).first()

        if payment:
            if result_code == 0:
                payment.status = 'Paid'
            else:
                payment.status = 'Failed'
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"MPESA callback error: {str(e)}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


@tenant_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Ensure the user is a tenant
    if current_user.role != 'tenant':
        flash('Access restricted to tenants.', category='error')
        return redirect(url_for('auth.login'))

    # 2. Fetch ALL data needed for the dashboard in one place

    # This is our new "smart" list for the main booking card(s)
    active_bookings = Booking.query.filter(
        Booking.tenant_id == current_user.id,
        Booking.status.notin_(['Rejected', 'Revoked', 'Expired', 'Cancelled'])
    ).order_by(Booking.created_at.desc()).all()

    # These are for your other cards (Payment History, Maintenance, etc.)
    payments = Payment.query.filter_by(
        tenant_id=current_user.id
    ).order_by(Payment.date.desc()).all()
    
    maintenance_requests = MaintenanceRequest.query.filter_by(
        tenant_id=current_user.id
    ).order_by(MaintenanceRequest.date_submitted.desc()).all()
    
    notifications = Notification.query.filter_by(
        tenant_id=current_user.id
    ).order_by(Notification.date.desc()).all()
    
    events = Event.query.filter_by(tenant_id=current_user.id).all()

    # This is for your "Open Requests" stat card
    open_requests_count = len([
        req for req in maintenance_requests
        if req.status.lower() in ['open', 'in progress']
    ])
    
    # --- ✅ NEW LOGIC TO FIND THE PRIMARY LANDLORD ---
    landlord = None
    confirmed_booking = None
    for b in active_bookings:
        if b.status == 'Confirmed':
            confirmed_booking = b
            break
    
    if confirmed_booking and confirmed_booking.house and confirmed_booking.house.owner:
        landlord = confirmed_booking.house.owner
    # This is for your "Next Payment" stat card
    # We update the logic to get the *correct* next payment from our new plan
    next_payment = None
    confirmed_booking = Booking.query.filter_by(
        tenant_id=current_user.id, 
        status='Confirmed'
    ).first()
    
    if confirmed_booking and confirmed_booking.next_rent_payment_due:
         next_payment = {
             'due_date': confirmed_booking.next_rent_payment_due,
             'amount': confirmed_booking.house.rent_amount
         }

    # This is for your "Payment Trends" chart
    payment_labels = [p.date.strftime('%b %Y') for p in payments]
    payment_data = [p.amount for p in payments]

    # 3. Render the template ONE time with ALL the data
    return render_template(
        'tenant.html',
        active_bookings=active_bookings,  # For our new main card
        payments=payments,
        maintenance_requests=maintenance_requests,
        notifications=notifications,
        events=events,
        open_requests_count=open_requests_count,
        next_payment=next_payment,
        payment_labels=payment_labels,
        payment_data=payment_data,
        landlord=landlord
        # We REMOVE the old 'property', 'landlord', and 'bookings' variables
        # because they are now replaced by the 'active_bookings' loop
    )
# Make a booking for a house
@tenant_bp.route('/book/<int:house_id>', methods=['GET', 'POST'])
@login_required
def bookings(house_id):
    # 🏠 Fetch the house details
    house = House.query.get_or_404(house_id)

    # ✅ Initialize Booking Form
    form = BookingForm()

    if form.validate_on_submit():
        # 🗓️ Get move-in date safely
        move_in_date = form.move_in_date.data

        # 🧾 Create the booking
        booking = Booking(
            tenant_id=current_user.id,
            house_id=house.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            current_address=form.current_address.data,
            move_in_date=move_in_date,  # ✅ Tenant's chosen move-in date
            lease_term=form.lease_term.data,
            special_requests=form.special_requests.data,
            occupants_count=form.occupants_count.data,
            pets=form.pets.data,
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            emergency_contact_relationship=form.emergency_contact_relationship.data,
            payment_method=form.payment_method.data,
            status="Pending",
            created_at=date.today()
        )

        # 💾 Save to database
        db.session.add(booking)
        db.session.commit()

        flash("✅ Booking request submitted successfully!", "success")

        # ✅ Redirect back to property details
        return redirect(url_for('tenant.property_details', house_id=house.id))

    # 📄 Render booking form page
    return render_template('tenant/book_property.html', house=house, form=form)





@tenant_bp.route("/properties", methods=['GET'])
def properties():
    query = request.args.get('query', '')
    is_guest = not current_user.is_authenticated
    print(f"Search query: {query}, Guest: {is_guest}")
    if query:
        houses = House.query.filter(
            (House.location.ilike(f'%{query}%')) |
            (House.title.ilike(f'%{query}%'))
        ).all()
    else:
        houses = House.query.all()
    print(f"Found houses: {len(houses)}")
    return render_template('index.html', houses=houses, query=query, is_guest=is_guest)

@tenant_bp.route('/booking/<int:booking_id>')
@login_required
def booking_page(booking_id):
    # Fetch booking from database
    booking = Booking.query.get_or_404(booking_id)

    # Ensure the current tenant owns this booking
    if booking.tenant_id != current_user.id:
        os.abort(403)
    
    if booking.status == 'Pending':
        flash('This booking is still awaiting landlord approval.', 'info')
        return redirect(url_for('tenant.all_bookings'))
    if booking.status == 'Confirmed':
        flash('You have already paid the deposit for this booking.', 'success')
        return redirect(url_for('tenant.all_bookings'))
    if booking.status not in ['Awaiting Deposit']:
        flash('This booking cannot be paid for.', 'danger')
        return redirect(url_for('tenant.all_bookings'))
    
    # Convert to dictionary for template
    #booking_data = booking_to_dict(booking)

    # Render template
    return render_template('tenant/tenant_booking_page.html', booking=booking)



@tenant_bp.route('/upload_document', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'document' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)

        file = request.files['document']
        if file.filename == '':
            flash("No file selected", "danger")
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            flash("Document uploaded successfully!", "success")
            return redirect(url_for('tenant.dashboard'))

    return render_template('upload_document.html')

# routes/tenant_routes.py

@tenant_bp.route('/documents', methods=['GET'])
@login_required
def documents():
    # Fetch documents belonging to the logged-in tenant
    tenant_documents = Document.query.filter_by(tenant_id=current_user.id).all()

    return render_template('documents.html', documents=tenant_documents)


@tenant_bp.route('/announcements')
@login_required
def announcements():
    # TODO: fetch announcements from DB when you add a model
    return render_template('tenant/announcements.html')




@tenant_bp.route('/lease/<int:id>')
def lease(id):
    # Your logic here
    return render_template('lease.html', lease_id=id)


# -----------------------------
# Process Payment (Mock Gateway)
# -----------------------------
@tenant_bp.route('/process_payment/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def process_payment(payment_id):
    payment = Payment.query.filter_by(id=payment_id, tenant_id=current_user.id).first_or_404()

    if request.method == 'POST':
        # Simulate payment success (replace with real gateway integration)
        payment.status = 'Paid'
        payment.date = datetime.utcnow()
        db.session.commit()

        # Generate receipt
        receipt = receipt(
            tenant_id=current_user.id,
            payment_id=payment.id,
            amount=payment.amount,
            date=datetime.utcnow()
        )
        db.session.add(receipt)
        db.session.commit()

        flash("Payment successful! Receipt generated.", "success")
        return redirect(url_for('tenant.receipts'))

    return render_template('process_payment.html', payment=payment)

# -----------------------------
# Payment History
# -----------------------------
@tenant_bp.route('/payment_history')
@login_required
def payment_history():
    payments = Payment.query.filter_by(tenant_id=current_user.id).order_by(Payment.date.desc()).all()
    return render_template('tenant/payment_history.html', payments=payments)
# -----------------------------
# Receipts
# -----------------------------
# @tenant_bp.route('/receipts')
# @login_required
# def receipts():
#     # ✅ FIX: Query the 'Payment' model, not the 'receipts' variable
#     # We also filter for 'Paid' status to only show completed receipts
#     all_receipts = Payment.query.filter_by(
#         tenant_id=current_user.id, 
#         status='Paid'
#     ).order_by(Payment.date.desc()).all()

#     return render_template('tenant/receipt.html', receipts=all_receipts)

@tenant_bp.route('/submit_request', methods=['GET', 'POST'])
@login_required
def submit_request():
    if request.method == 'POST':
        issue = request.form.get('issue')
        if not issue:
            flash("Please describe the issue before submitting.", "danger")
            return redirect(url_for('tenant.submit_request'))

        request_obj = MaintenanceRequest(
            tenant_id=current_user.id,
            issue=issue,
            status="Open",
            date_submitted=datetime.utcnow()
        )
        db.session.add(request_obj)
        db.session.commit()

        flash("Maintenance request submitted successfully!", "success")
        return redirect(url_for('tenant.dashboard'))

    return render_template('submit_request.html')

@tenant_bp.route('/requests')
@login_required
def requests():
    # This is the page for the "View All" link
    all_requests = MaintenanceRequest.query.filter_by(
        tenant_id=current_user.id
    ).order_by(MaintenanceRequest.date_submitted.desc()).all()
    
    # You'll need to create a new template for this: 'tenant_requests.html'
    return render_template('tenant/tenant_requests.html', requests=all_requests)
# -----------------------------
# Pay Rent - Submit Payment
# -----------------------------
@tenant_bp.route('/pay_rent', methods=['GET', 'POST'])
@login_required
def pay_rent():
    # Find the tenant's confirmed booking
    booking = Booking.query.filter_by(
        tenant_id=current_user.id,
        status='Confirmed'
    ).first()

    if not booking:
        flash("You do not have an active, confirmed booking.", "danger")
        return redirect(url_for('tenant.dashboard'))

    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            if amount != booking.house.rent_amount:
                flash(f"Incorrect rent amount. Please pay KES {booking.house.rent_amount}.", "danger")
                return redirect(url_for('tenant.pay_rent'))
        except (ValueError, TypeError):
            flash("Please enter a valid numeric amount.", "danger")
            return redirect(url_for('tenant.pay_rent'))

        # Here you would call your MPESA STK push logic
        # For now, we simulate success just like in your /process_payment route
        
        # 1. Create the Payment record for this rent payment
        rent_payment = Payment(
            tenant_id=current_user.id,
            booking_id=booking.id,
            amount=amount,
            date=datetime.utcnow(),
            status='Paid',
            # e.g., "Rent - November 2025"
            payment_for=f"Rent - {booking.next_rent_payment_due.strftime('%B %Y')}",
            receipt_id=f"RCPT-{uuid.uuid4().hex[:10].upper()}"
        )
        
        # 2. Update the *next* payment due date
        # (This assumes monthly payment, update as-needed)
        booking.next_rent_payment_due = booking.next_rent_payment_due + relativedelta(months=1)
        
        db.session.add(rent_payment)
        db.session.commit()
        
        flash("Rent paid successfully! A receipt has been generated.", "success")
        return redirect(url_for('tenant.payment_history'))

    return render_template('pay_rent.html', booking=booking)


@tenant_bp.route('/profile', methods=['GET', 'POST']) # <-- Add 'POST'
@login_required
def profile():
    if request.method == 'POST':
        # Handle the form submission
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        # ... handle profile picture upload ...
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('tenant.profile'))

    return render_template('profile.html', tenant=current_user)

@tenant_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        feedback_text = request.form['feedback']
        # Save feedback to DB (you’ll need a Feedback model)
        # feedback = Feedback(tenant_id=current_user.id, content=feedback_text)
        # db.session.add(feedback)
        # db.session.commit()
        return redirect(url_for('tenant.dashboard'))
    
    return render_template('tenant_feedback.html')


@tenant_bp.route('/2fa_setup', methods=['GET', 'POST'])
@login_required
def twofa_setup():
    # Ensure the user is a tenant
    if current_user.role != 'tenant':
        flash('Access restricted to tenants.', category='error')
        return redirect(url_for('tenant.dashboard'))

    if request.method == 'POST':
        # Handle 2FA setup form submission
        verification_code = request.form.get('verification_code')
        secret = current_user.two_factor_secret  # Assume secret is stored in user model

        if not secret:
            flash('2FA setup session expired. Please try again.', category='error')
            return redirect(url_for('tenant.2fa_setup'))

        # Verify the provided code
        totp = pyotp.TOTP(secret)
        if totp.verify(verification_code):
            current_user.two_factor_enabled = True
            db.session.commit()
            flash('2FA successfully enabled!', category='success')
            return redirect(url_for('tenant.dashboard'))
        else:
            flash('Invalid verification code. Please try again.', category='error')

    # GET request: Generate and display 2FA secret and QR code
    if not current_user.two_factor_secret:
        # Generate a new TOTP secret
        secret = pyotp.random_base32()
        current_user.two_factor_secret = secret
        db.session.commit()
    else:
        secret = current_user.two_factor_secret

    # Generate QR code for authenticator app
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name='HomeHub'
    )
    qr = qr_code.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('2fa_setup.html', qr_code=qr_code, secret=secret)

@tenant_bp.route('/move_out/<int:booking_id>', methods=['POST'])
@login_required
def move_out(booking_id):
    booking = Booking.query.filter_by(id=booking_id, tenant_id=current_user.id).first_or_404()
    booking.status = 'move_out_requested'
    db.session.commit()
    return redirect(url_for('tenant.dashboard'))

@tenant_bp.route('/Browse properties')
@login_required
def browse_properties():
    houses = House.query.filter_by(available=True).all()
    return render_template("properties.html", houses=houses)
    

# View all bookings
@tenant_bp.route('/all_bookings')
@login_required
def all_bookings():
    bookings = Booking.query.filter_by(tenant_id=current_user.id).all()
    return render_template('tenant/tenant_bookings.html', bookings=bookings)

@tenant_bp.route('/messages')
@login_required
def messages():
    if current_user.role != "tenant":
        flash("Access restricted to tenants.", "danger")
        return redirect(url_for("auth.login"))

    # Example: fetch messages from DB
    tenant_messages = Message.query.filter_by(tenant_id=current_user.id).all()

    return render_template("tenant/messages.html", messages=tenant_messages)

@tenant_bp.route('/receipt/<string:receipt_id>')
@login_required
def view_receipt(receipt_id):
    payment = Payment.query.filter_by(receipt_id=receipt_id).first_or_404()
    
    # Security check: must be the tenant
    if payment.tenant_id != current_user.id:
        # (We can also add a check for the landlord later)
        os.abort(403) 
        
    # Make sure you have created the 'tenant/receipt.html' template
    return render_template('tenant/receipt.html', payment=payment)

# Contact service providers
@tenant_bp.route('/contact_providers')
@login_required
def contact_providers():
    service_providers = User.query.filter_by(role='service').all()
    return render_template(
        'tenant.html',
        bookings=[],
        houses=[],
        service_providers=service_providers
    )

# Chat with landlord
@tenant_bp.route('/chat/history/<int:landlord_id>', methods=['GET'])
@login_required
def chat_history(landlord_id):
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == landlord_id)) |
        ((Message.sender_id == landlord_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    # Convert messages to a simple dictionary format for JSON
    messages_list = [
        {
            'sender_id': msg.sender_id,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages
    ]
    
    return jsonify(messages=messages_list)


# routes/tenant_routes.py

@tenant_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Only tenants can access
    if current_user.role != 'tenant':
        flash("Access restricted to tenants.", "error")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Example: update tenant profile settings
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        db.session.commit()
        flash("Settings updated successfully.", "success")

    return render_template("tenant_settings.html", user=current_user)


@tenant_bp.route('/notifications')
def view_notifications():
    # Fetch notifications
    return render_template('tenant/notifications.html')


# ✅ Tenant Property Details Route
@tenant_bp.route('/property/<int:house_id>', methods=['GET'])
@login_required
def property_details(house_id):
    # Fetch house record
    house = House.query.get_or_404(house_id)

    # Render property details page for tenants
    return render_template('tenant/property_details.html', property=house)


