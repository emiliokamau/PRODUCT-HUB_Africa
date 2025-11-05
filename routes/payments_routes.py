import requests
from flask import Blueprint, jsonify, request
from datetime import datetime
import base64

from models import Booking, House, PaymentMethods
from models.models import PaymentTransaction  # ✅ Import models

payments_bp = Blueprint('payments', __name__)

# ✅ Sandbox API Keys
CONSUMER_KEY = "0x6mfH2Buh4phYmChotKxOmuISKHNsoCPHGaJp9xtJ73kUzw"
CONSUMER_SECRET = "ICGbJnwdbEAJP6Ke6jSMuBDGGLTIkUStcZeDnNlMoOxISsl5w9tOeqAIUgaP3LiD"

# ✅ Passkey (remains same, used to generate password)
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

# ✅ Ngrok callback or your actual domain
CALLBACK_URL = "https://ethel-tillable-debera.ngrok-free.dev/api/mpesa/callback"

def get_mpesa_token():
    token_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(token_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json().get("access_token")

@payments_bp.route("/api/mpesa/callback", methods=["POST"])
def mpesa_callback():
    data = request.get_json()
    print("✅ Callback received:", data)

    try:
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        result_desc = body.get("ResultDesc")
        metadata = body.get("CallbackMetadata", {}).get("Item", [])

        booking_id = int(metadata[0]["Value"]) if metadata else None
        amount = None
        receipt = None
        phone = None

        for item in metadata:
            if item["Name"] == "Amount":
                amount = item["Value"]
            if item["Name"] == "MpesaReceiptNumber":
                receipt = item["Value"]
            if item["Name"] == "PhoneNumber":
                phone = item["Value"]

        if result_code == 0:
            # ✅ Save to DB
            payment = PaymentTransaction(
                booking_id=booking_id,
                house_id=Booking.query.get(booking_id).house_id,
                phone_number=phone,
                amount=amount,
                mpesa_receipt=receipt,
                status="Success",
                result_code=result_code
            )
            db.session.add(payment)

            # ✅ Mark booking as paid
            booking = Booking.query.get(booking_id)
            booking.payment_status = "Paid"
            db.session.commit()
            print("💰 Payment Recorded Successfully!")

        else:
            print("❌ Payment Failed:", result_desc)

        return jsonify({"ResultCode": 0, "ResultDesc": "Callback processed successfully"})

    except Exception as e:
        print("⚠ Callback Processing Error:", e)
        return jsonify({"ResultCode": 1, "ResultDesc": "Error processing callback"}), 500

