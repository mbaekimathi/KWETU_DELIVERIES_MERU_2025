# Kwetu Deliveries

A modern, responsive food delivery web application built with Flask, PyMySQL, and TailwindCSS.

## Features

- 🍔 Browse restaurants and food shops
- 🛒 Shopping cart functionality
- 📱 Fully responsive design (mobile, tablet, desktop)
- 🎨 Modern UI with orange and blue theme
- 👤 User authentication (Login/Register)
- 📊 Dashboard for Admin, Merchant, and Customer roles
- 🚀 Fast and efficient database operations with PyMySQL

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MySQL (via PyMySQL)
- **Frontend**: HTML5, JavaScript (ES6+), TailwindCSS
- **Templates**: Jinja2

## Installation

1. **Clone or download the project**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MySQL database**:
   - The database `MERU_DELIVERIES` will be created automatically on first run
   - Update database credentials in `app.py` (DB_CONFIG):
     ```python
     DB_CONFIG = {
         'host': 'localhost',
         'user': 'your_username',
         'password': 'your_password',
         ...
     }
     ```
   - The application will automatically check for the database and tables, creating them if they don't exist
   - All database changes are tracked in a `migrations` table for future updates

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the application**:
   - Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
MERU DELIVERIES/
├── app.py                 # Flask application with database initialization
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── static/
│   ├── css/
│   │   └── style.css     # Custom CSS styles
│   └── js/
│       └── main.js       # Main JavaScript file
└── templates/
    ├── base.html         # Base template (header, sidebar, footer)
    └── index.html        # Home page
```

## Database Schema

The application automatically creates the database `MERU_DELIVERIES` and the following tables on first run:

- **migrations**: Tracks all database schema changes for future updates
- **users**: User accounts (customer, merchant, admin)
- **shops**: Restaurant/shop information
- **menu_items**: Menu items for each shop
- **orders**: Customer orders
- **order_items**: Items in each order

### Database Initialization

The application performs detailed checks:
1. Verifies if the database exists, creates it if missing
2. Checks each table's existence and structure
3. Creates missing tables with proper indexes and foreign keys
4. Records all changes in the `migrations` table for tracking

This ensures that when you deploy to a hosting environment, the application will automatically set up the database structure and track any schema changes.

## Features

### Home Page (`/`)
- Hero section with call-to-action
- Featured shops display
- "How it works" section
- Clean, responsive design with orange and blue theme

## Customization

### Theme Colors
The theme uses orange and blue colors defined in `templates/base.html`:
- Primary Orange: `#FF6B35`
- Primary Blue: `#004E89`
- Light Orange: `#FF8C5A`
- Light Blue: `#1A6BA3`

### Adding Sample Data
You can add sample data directly to the database or create a script to populate it:

```python
# Example: Add a shop
connection = get_db_connection()
with connection.cursor() as cursor:
    cursor.execute("""
        INSERT INTO shops (name, description, rating, delivery_time)
        VALUES (%s, %s, %s, %s)
    """, ("Sample Restaurant", "Delicious food", 4.5, "30-45 min"))
connection.commit()
```

## Security Notes

⚠️ **Important**: This is a starter template. For production use:

1. Use password hashing (bcrypt, werkzeug.security)
2. Implement CSRF protection
3. Use environment variables for sensitive data
4. Add input validation and sanitization
5. Implement proper error handling
6. Use HTTPS
7. Add rate limiting
8. Implement proper session management

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

This project is provided as-is for educational and development purposes.

## Contributing

Feel free to extend this application with additional features:
- Payment gateway integration
- Real-time order tracking
- Push notifications
- Advanced search and filters
- Reviews and ratings system
- Image upload functionality

## Support

For issues or questions, please check the code comments or create an issue in your repository.

---

**Built with ❤️ for food delivery**

