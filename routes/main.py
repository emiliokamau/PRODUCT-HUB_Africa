from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.models import House, db
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    houses = House.query.all()
    return render_template('index.html', houses=houses)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/accessibility')
def accessibility():
    return render_template('accessibility.html')

@main_bp.route('/subscribe')
def subscribe():
    return render_template('subscribe.html')

@main_bp.route('/help')
def help():
    return render_template('help.html')

@main_bp.route('/help/search_results')
def help_search_results():
    query = request.args.get('q')
    # maybe search FAQs or docs here
    results = []
    return render_template('help_search_results.html', query=query, results=results)

# Landlord Help Page
@main_bp.route('/help/landlord')
def help_landlord():
    return render_template('help_landlord.html')


# Tenant Help Page
@main_bp.route('/help/tenant')
def help_tenant():
    return render_template('help_tenant.html')


# Service Provider Help Page
@main_bp.route('/help/service-provider')
def help_service_provider():
    return render_template('help_service_provider.html')


# Admin Help Page
@main_bp.route('/help/admin')
def help_admin():
    return render_template('help_admin.html')

@main_bp.route('/help/general')
def help_general():
    return render_template('help_general.html')



@main_bp.route('/how-it-works')
def how_it_works_general():
    return render_template('how_it_works.html')


@main_bp.route('/how-it-works/landlord')
def how_it_works_landlord():
    return render_template('how_it_works_landlord.html')

@main_bp.route('/how-it-works/tenant')
def how_it_works_tenant():
    return render_template('how_it_works_tenant.html')

@main_bp.route('/how-it-works/provider')
def how_it_works_provider():
    return render_template('how_it_works_provider.html')

@main_bp.route('/how-it-works/admin')
def how_it_works_admin():
    return render_template('how_it_works_admin.html')

@main_bp.route('/how-it-works/<role>')
def how_it_works(role):
    return render_template(f"how_it_works_{role}.html")



@main_bp.route('/subscribe', methods=['POST'])
def subscribe_post():
    email = request.form.get('email')
    if email:
        flash(f'Subscribed successfully with {email}', 'success')
    else:
        flash('No email provided', 'danger')
    return redirect(url_for('main.index'))

@main_bp.route('/properties')
def properties_list():
    # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = 12
        query = request.args.get('query', '')
        property_type = request.args.get('property_type', '')
        price_range = request.args.get('price_range', '')
        bedrooms = request.args.get('bedrooms', '', type=int)
        sort = request.args.get('sort', 'newest')
    
    
    # Start with base query
        houses_query = House.query.filter_by(available=True)
        #.order_by(House.id.desc()).get(id).all()----------causes a crash
         # --- DEBUGGING PRINT ---
    # This will print in your terminal. Check it to see the values.
        print(f"URL Parameters -> query: '{query}', type: '{property_type}', price: '{price_range}', beds: '{bedrooms}'")
        
        all_properties = House.query.all()
        print(f"DEBUG: Total properties in DB: {len(all_properties)}")
        for prop in all_properties:
            print(f"  - ID: {prop.id}, Title: {prop.title}, Available: {prop.available}")
    # --- END DEBUGGING STEP ---
    
    # Apply filters
        if query:
           houses_query = houses_query.filter(
                db.or_(
                    House.title.contains(query),
                    House.description.contains(query),
                    House.location.contains(query)
                )
            )
    
        if property_type:
            houses_query = houses_query.filter(House.property_type == property_type)
    
        if price_range:
            if price_range == '0-10000':
                houses_query = houses_query.filter(House.price <= 10000)
            elif price_range == '10000-25000':
                houses_query = houses_query.filter(House.price.between(10000, 25000))
            elif price_range == '25000-50000':
                houses_query = houses_query.filter(House.price.between(25000, 50000))
            elif price_range == '50000+':
                houses_query = houses_query.filter(House.price > 50000)
    
        if bedrooms:
            houses_query = houses_query.filter(House.bedrooms == bedrooms)
    
    # Apply sorting
        if sort == 'newest':
            houses_query = houses_query.order_by(House.id.desc())
        elif sort == 'price_low':
            houses_query = houses_query.order_by(House.rent_amount.asc())
        elif sort == 'price_high':
            houses_query = houses_query.order_by(House.rent_amount.desc())
        elif sort == 'popular':
        # This would need additional logic based on views, bookings, etc.
            houses_query = houses_query.order_by(House.id.desc())
    
    # Paginate results
        houses = houses_query.paginate(page=page, per_page=per_page, error_out=False)
    # --- ANOTHER DEBUGGING STEP ---
        print(f"DEBUG: Properties after filtering/pagination: {len(houses.items)}")
    # --- END DEBUGGING STEP ---
    # Calculate total pages for pagination
        #total_pages = properties.pages
    
        return render_template(
            'properties.html',
            properties=houses.items,
            page=page,
            #total_pages=houses_pages,
            query=query,
            property_type=property_type,
            price_range=price_range,
            bedrooms=bedrooms,
            sort=sort,
            is_guest=not current_user.is_authenticated
          
        )

@main_bp.route('/property/<int:house_id>')
def view_property(house_id):
    property = House.query.get_or_404(house_id)
    # Use image_urls instead of images
    image_list = [img.strip().split('/')[-1] for img in property.image_urls.split(',')] if property.image_urls else []
    print(f"Raw image_urls from DB: {property.image_urls}")  # Debug
    print(f"Processed image_list: {image_list}")  # Debug
    return render_template('view_property.html', property=property, image_list=image_list)


