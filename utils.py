import os
from datetime import date, datetime

def house_to_dict(house):
    return {
        'id': house.id,
        'title': house.title,
        'description': house.description,
        'location': house.location,
        'lat': house.lat,
        'lng': house.lng,
        'category': house.category,
        'image_urls': [os.path.basename(url) for url in (house.image_urls.split(',') if house.image_urls else [])]
    }

def booking_to_dict(booking):
    def format_date(d):
        if isinstance(d, (date, datetime)):
            return d.strftime('%d %b %Y')
        elif isinstance(d, str):
            return d  # Already a string
        return None

    return {
        "id": booking.id,
        "status": booking.status,
        "lease_term": booking.lease_term,
        "move_in_date": format_date(booking.move_in_date),
        "special_requests": booking.special_requests or 'None',
        "created_at": format_date(booking.created_at),
        "updated_at": format_date(getattr(booking, 'updated_at', None)),  # <-- added safely
        "house_title": booking.house.title if booking.house else 'Unknown',
        "house_address": f"{booking.house.address_line1}, {booking.house.city}" if booking.house else 'Unknown',
        "owner_email": booking.house.owner.email if booking.house and booking.house.owner else 'Unknown',
        "tenant_name": f"{booking.first_name} {booking.last_name}",
        "tenant_email": booking.email,
        "tenant_phone": booking.phone,
        "stay_duration": booking.stay_duration,
        "deposit_paid": booking.deposit_paid,
        "payment_method": booking.payment_method,
        "agree_terms": booking.agree_terms
    }
