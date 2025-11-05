import os
import logging
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import date, datetime
from extensions import db, csrf
from models.models import User, House, Booking, Payment, MaintenanceRequest, ServiceProvider, PaymentMethods




# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Blueprint setup
landlord_bp = Blueprint("landlord", __name__, url_prefix="/landlord")

# Allowed image extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Landlord Dashboard ----------------
@landlord_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # Fetch houses and tenants
    houses = House.query.filter_by(owner_id=current_user.id).all()
    tenants = (
        db.session.query(User, Booking, House)
        .join(Booking, Booking.tenant_id == User.id)
        .join(House, Booking.house_id == House.id)
        .filter(User.role == "tenant", House.owner_id == current_user.id)
        .all()
    )

    # -------------------------
    # Calculate simple dashboard stats (replace with your real logic)
    # -------------------------
    total_properties = len(houses)
    total_tenants = len(tenants)

    # Calculate occupancy rate
    occupied_units = sum(1 for h in houses if any(t[2].id == h.id for t in tenants))
    occupancy_rate = (occupied_units / total_properties * 100) if total_properties > 0 else 0

    # Example monthly revenue (replace with actual query later)
    total_revenue = db.session.query(db.func.sum(Payment.amount))\
        .join(Booking, Payment.tenant_id == Booking.tenant_id)\
        .join(House, Booking.house_id == House.id)\
        .filter(House.owner_id == current_user.id)\
        .scalar() or 0

    # 🧮 These change values can be dynamic later — set to 0 for now
    stats = {
        "total_properties": total_properties,
        "properties_change": 0,      # TODO: calculate vs. last period
        "occupancy_rate": round(occupancy_rate, 2),
        "occupancy_change": 0,       # TODO: calculate vs. last period
        "monthly_revenue": int(total_revenue),
        "revenue_change": 0,         # TODO: calculate vs. last period
        "requests_change": 0         # TODO: calculate vs. last period
    }

    # Maintenance requests (for dashboard count)
    maintenance_requests = (
        db.session.query(MaintenanceRequest, User, House)
        .join(User, MaintenanceRequest.tenant_id == User.id)
        .join(Booking, Booking.tenant_id == User.id)
        .join(House, Booking.house_id == House.id)
        .filter(House.owner_id == current_user.id)
        .all()
    )

    return render_template(
        "landlord/dashboard.html",
        houses=houses,
        tenants=tenants,
        stats=stats,
        maintenance_requests=maintenance_requests
    )



# ---------------- Manage Properties ----------------
@landlord_bp.route("/properties")
@login_required
def properties():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    try:
        properties = House.query.filter_by(owner_id=current_user.id).all()
        print(f"Retrieved properties count: {len(properties)}")
        for prop in properties:
            print(f"Property {prop.id} data: "
                  f"title={prop.title}, "
                  f"image_urls={prop.image_urls}, "
                  f"available={prop.available}, "
                  f"availability_date={prop.availability_date}, "
                  f"state_province={prop.state_province}, "
                  f"city={prop.city}")
        return render_template("landlord/properties.html", properties=properties, stats={})
    except Exception as e:
        print(f"🔥 ERROR listing properties: {str(e)}")
        import traceback
        traceback.print_exc()
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for("landlord.properties"))


import os
from werkzeug.utils import secure_filename
from flask import current_app



# ---------------- Add Property ----------------
@landlord_bp.route("/properties/add", methods=["GET", "POST"])
@login_required
def add_property():

    houses = db.session.query(House, PaymentMethods).outerjoin(
    PaymentMethods, PaymentMethods.house_id == House.id
    ).all()
    
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        try:
            # 📝 Basic property info
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if len(description) > 500:
                return jsonify({
                        "success": True,
                        "message": "✅ Property added successfully!",
                        "redirect": url_for("landlord.dashboard")
                    })


            property_type = request.form.get("property_type", "").strip()
            city = request.form.get("county", "").strip()
            state_province = request.form.get("estate_area", "").strip()
            address_line1 = request.form.get("address", "").strip()
            building_name = request.form.get("building_name", "").strip()
            house_number = request.form.get("house_number", "").strip()
            country = "Kenya"
            
            try:
                rent_amount = float(request.form.get("rent_amount") or 0)
                security_deposit = float(request.form.get("security_deposit") or 0)
                bedrooms = int(request.form.get("bedrooms") or 0) if request.form.get("bedrooms") not in ["Studio"] else 0
                bathrooms = float(request.form.get("bathrooms") or 0)
                size = request.form.get("size", "0").strip()
            except ValueError:
                flash("Invalid numeric input for rent, deposit, bedrooms, bathrooms, or size.", "danger")
                return redirect(url_for("landlord.add_property"))

            lease_term = request.form.get("payment_frequency", "").strip()
            try:
                availability_date = datetime.strptime(
                    request.form.get("availability_date"), "%Y-%m-%d"
                ).date() if request.form.get("availability_date") else date.today()
            except ValueError:
                flash("Invalid date format for availability date.", "danger")
                return redirect(url_for("landlord.add_property"))

            utilities = ",".join(request.form.getlist("utilities")) if request.form.getlist("utilities") else ""
            amenities = ",".join(request.form.getlist("amenities")) if request.form.getlist("amenities") else ""
            pets_allowed = request.form.get("pets_policy", "Not Allowed").strip()
            smoking_policy = request.form.get("smoking_policy", "Not Allowed").strip()
            parking_availability = "Yes" if "Parking" in request.form.getlist("amenities") else "No"
            furnished_status = request.form.get("furnishing", "Unfurnished").strip()

            # 📸 Handle multiple image uploads
            image_files = request.files.getlist("images")
            image_urls = []
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'properties')
            print(f"Upload directory: {upload_dir}")  # Debug: Check directory
            os.makedirs(upload_dir, exist_ok=True)

            if len(image_files) > 5:
                flash("Maximum 5 images allowed.", "danger")
                return redirect(url_for("landlord.add_property"))

            # Deduplicate and process files
            processed_filenames = set()
            for image_file in image_files:
                if image_file and image_file.filename:
                    filename = secure_filename(image_file.filename)
                    if filename in processed_filenames:
                        print(f"Skipping duplicate file: {filename}")  # Debug: Duplicate
                        continue
                    processed_filenames.add(filename)
                    print(f"Processing file: {filename}")  # Debug: Track file

                    if not allowed_file(filename):
                        print(f"File {filename} not allowed.")  # Debug: Invalid type
                        flash("Only JPG and PNG images are allowed.", "danger")
                        continue

                    # Get file size
                    image_file.seek(0, os.SEEK_END)
                    file_size = image_file.tell()
                    image_file.seek(0)
                    print(f"File size: {file_size} bytes")  # Debug: Check size


                    if file_size > MAX_FILE_SIZE:
                        print(f"File {filename} exceeds 5MB.")  # Debug: Size limit
                        flash("Image size exceeds 5MB limit.", "danger")
                        continue

                    # Generate unique filename
                    if '.' not in filename:
                        ext = 'jpg'  # Default extension
                    else:
                        ext = filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{ext}"
                    upload_path = os.path.join(upload_dir, unique_filename)
                    print(f"Saving to: {upload_path}")  # Debug: Check save path

                    try:
                        image_file.save(upload_path)
                        if os.path.exists(upload_path):
                            print(f"Successfully saved: {unique_filename}")  # Debug: Confirm save
                            image_urls.append(f"uploads/properties/{unique_filename}")
                        else:
                            print(f"Save failed for: {unique_filename}")  # Debug: File not created
                            flash("Failed to save an image. Check server permissions.", "danger")
                    except Exception as save_error:
                        print(f"Save error for {unique_filename}: {str(save_error)}")  # Debug: Save exception
                        flash(f"Error saving image: {str(save_error)}", "danger")
                        continue

            # Use default image only if no valid images were saved
            if not image_urls:
                print("No valid images uploaded, using default.")  # Debug: Fallback trigger
                image_urls = ["images/default-house.jpg"]

            image_urls_str = ",".join(image_urls)
            print(f"Final image_urls: {image_urls_str}")  # Debug: Final URL string

            # ✅ Collect Payment Method Data from Form
            mpesa_till_number = request.form.get("mpesa_till_number")
            mpesa_business_name = request.form.get("mpesa_business_name")
            mpesa_enabled = bool(request.form.get("mpesa_enabled"))

            paybill_number = request.form.get("paybill_number")
            paybill_account_number = request.form.get("paybill_account_number")
            paybill_enabled = bool(request.form.get("paybill_enabled"))

            bank_name = request.form.get("bank_name")
            bank_branch = request.form.get("bank_branch")
            account_name = request.form.get("account_name")
            account_number = request.form.get("account_number")
            bank_enabled = bool(request.form.get("bank_enabled"))

            send_money_phone = request.form.get("send_money_phone")
            send_money_name = request.form.get("send_money_name")
            send_money_enabled = bool(request.form.get("send_money_enabled"))


            # 🏠 Create and commit house object
            house = House(
                title=title,
                description=description,
                property_type=property_type,
                image_urls=image_urls_str,
                location=f"{state_province}, {city}",
                available=True,
                owner_id=current_user.id,
                address_line1=address_line1,
                address_line2=building_name + " " + house_number if building_name or house_number else None,
                city=city,
                state_province=state_province,
                postal_code="",
                country=country,
                rent_amount=rent_amount,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                size=size,
                lease_term=lease_term,
                availability_date=availability_date,
                utilities=utilities,
                pets_allowed=pets_allowed,
                parking_availability=parking_availability,
                furnished_status=furnished_status,
                amenities=amenities,
                security_deposit=security_deposit,
                smoking_policy=smoking_policy
            )

            db.session.add(house)
            db.session.commit()

            payment = PaymentMethods(
            house_id=house.id,
            mpesa_till_number=mpesa_till_number,
            mpesa_business_name=mpesa_business_name,
            mpesa_enabled=mpesa_enabled,
            paybill_number=paybill_number,
            paybill_account_number=paybill_account_number,
            paybill_enabled=paybill_enabled,
            bank_name=bank_name,
            bank_branch=bank_branch,
            account_name=account_name,
            account_number=account_number,
            bank_enabled=bank_enabled,
            send_money_phone=send_money_phone,
            send_money_name=send_money_name,
            send_money_enabled=send_money_enabled
        )

            db.session.add(payment)
            db.session.commit()
            print("Property committed to database.")  # Debug: Confirm commit

            return jsonify({
    "success": True,
    "message": "✅ Property added successfully!",
    "redirect": url_for("landlord.dashboard")
})


        except Exception as e:
            db.session.rollback()
            print(f"🔥 ERROR adding property: {str(e)}")  # Debug: Log exact error
            import traceback
            traceback.print_exc()
            flash(f"❌ Error adding property: {str(e)}", "danger")
            return redirect(url_for("landlord.add_property"))

    return render_template("landlord/add_property.html", stats={})


@landlord_bp.route("/delete_property/<int:property_id>", methods=["POST"])
@login_required
def delete_property(property_id):
    house = House.query.get_or_404(property_id)
    try:
        db.session.delete(house)
        db.session.commit()
        return jsonify({"success": True, "message": "Property deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to delete property"}), 500


@landlord_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    # your update logic here
    return redirect(url_for('landlord.settings'))












# ---------------- Manage Tenants ----------------
@landlord_bp.route("/tenants")
@login_required
def tenants():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # ✅ Get all bookings tied to houses owned by this landlord
    bookings = (
        Booking.query
        .join(House, Booking.house_id == House.id)
        .filter(House.owner_id == current_user.id)
        .options(db.joinedload(Booking.tenant), db.joinedload(Booking.house))
        .all()
    )

    # ✅ Compute house stats
    houses = House.query.filter_by(owner_id=current_user.id).all()
    total_houses = len(houses)
    occupied_count = sum(1 for h in houses if any(b.house_id == h.id for b in bookings))
    vacant_count = total_houses - occupied_count

    # ✅ Maintenance request stats
    pending_requests = (
        db.session.query(MaintenanceRequest)
        .join(House, MaintenanceRequest.house_id == House.id)
        .filter(House.owner_id == current_user.id, MaintenanceRequest.status == "Pending")
        .count()
    )

    approved_requests = (
        db.session.query(MaintenanceRequest)
        .join(House, MaintenanceRequest.house_id == House.id)
        .filter(House.owner_id == current_user.id, MaintenanceRequest.status == "Approved")
        .count()
    )

    rejected_requests = (
        db.session.query(MaintenanceRequest)
        .join(House, MaintenanceRequest.house_id == House.id)
        .filter(House.owner_id == current_user.id, MaintenanceRequest.status == "Rejected")
        .count()
    )

    # ✅ Stats dictionary (make sure all keys used in template exist)
    stats = {
        "total_tenants": len(bookings),
        "occupied_count": occupied_count,
        "vacant_count": vacant_count,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "rejected_requests": rejected_requests,
        "approved_change": 3,     # you can later calculate actual changes
        "rejected_change": -2,    # placeholder until dynamic
    }

    return render_template("landlord/tenants.html", bookings=bookings, stats=stats)






# ---------------- Payments ----------------
@landlord_bp.route("/payments")
@login_required
def payments():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    payments = (
        db.session.query(Payment, User, House)
        .join(User, Payment.tenant_id == User.id)
        .join(Booking, Booking.tenant_id == User.id)
        .join(House, Booking.house_id == House.id)
        .filter(House.owner_id == current_user.id)
        .all()
    )
    return render_template("landlord/payments.html", payments=payments, stats={})

@landlord_bp.route("/announcements")
@login_required
def announcements():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # Here you can later fetch announcements from the database
    announcements_list = [
        {"title": "Water Maintenance", "message": "Water will be off on Friday", "date": "2025-10-13"},
        {"title": "Security Notice", "message": "Gate lock changed, new code shared", "date": "2025-10-14"}
    ]

    return render_template("landlord/announcements.html", announcements=announcements_list)



@landlord_bp.route('/notifications')
@login_required
def notifications():
    # You can fetch notifications for landlord here
    notifications = []  # Example placeholder
    return render_template('landlord/notifications.html', notifications=notifications)

@landlord_bp.route("/properties/<int:id>")
@login_required
def view_property(id):
    house = House.query.get_or_404(id)
    return render_template("landlord/view_property.html", properties=properties)




# ---------------- Maintenance Requests ----------------
@landlord_bp.route("/maintenance")
@login_required
def maintenance():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    requests = (
        db.session.query(MaintenanceRequest, User, House)
        .join(User, MaintenanceRequest.tenant_id == User.id)
        .join(Booking, Booking.tenant_id == User.id)
        .join(House, Booking.house_id == House.id)
        .filter(House.owner_id == current_user.id)
        .all()
    )
    return render_template("landlord/maintenance.html", requests=requests, stats={})


# ---------------- Service Providers ----------------
@landlord_bp.route("/service-providers")
@login_required
def service_providers():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    providers = ServiceProvider.query.all()
    return render_template("landlord/service_providers.html", providers=providers, stats={})


# ---------------- Reports ----------------
@landlord_bp.route("/reports")
@login_required
def reports():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))
    return render_template("landlord/reports.html", stats={})


# ---------------- Edit Property ----------------
@landlord_bp.route("/properties/<int:property_id>/edit", methods=["GET", "POST"])
@login_required
def edit_property(property_id):
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    house = House.query.filter_by(id=property_id, owner_id=current_user.id).first_or_404()

    if request.method == "POST":
        house.title = request.form.get("title")
        house.description = request.form.get("description")
        house.location = request.form.get("location")
        house.rent_amount = request.form.get("rent_amount")

        db.session.commit()
        flash("Property updated successfully!", "success")
        return redirect(url_for("landlord.properties"))

    return render_template("landlord/edit_property.html", house=house, stats={})



# ---------------- Settings ----------------
@landlord_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # Mock settings data
    settings = {
        "company_name": "My Property Co.",
        "dark_mode": False,
        "compact_view": False,
        "public_profile": True,
        "show_contact": True,
        "share_stats": False,
    }

    if request.method == "POST":
        flash("Settings updated successfully!", "success")
        return redirect(url_for("landlord.settings"))

    return render_template("landlord/settings.html", settings=settings)



# ---------------- Messages ----------------
@landlord_bp.route("/messages")
@login_required
def messages():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # TODO: Load landlord messages
    return render_template("landlord/messages.html", stats={})


# ---------------- Profile ----------------
@landlord_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.role != "landlord":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        current_user.name = request.form.get("name")
        current_user.email = request.form.get("email")
        current_user.phone_number = request.form.get("phone_number")

        if "profile_picture" in request.files:
            picture = request.files["profile_picture"]
            if picture:
                filename = secure_filename(picture.filename)
                filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                picture.save(filepath)
                current_user.profile_picture = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("landlord.profile"))

    return render_template("landlord/profile.html", stats={})
