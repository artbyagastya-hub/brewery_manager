# 🍺 Brewery Manager

A comprehensive brewery management system built for Vietnamese craft breweries. This system helps manage everything from recipes and production to sales, accounting, and compliance.

## Features

### ✅ Sprint 1: Recipe & Yeast Management (COMPLETED)
- **Recipe Database**: Store and manage beer recipes with ingredients, mash schedules, boil schedules, and fermentation profiles
- **Yeast Management**: Track yeast strains, generations, viability, and pitching rates
- **Recipe Calculator**: Calculate ABV, IBU, SRM, OG/FG, and batch scaling
- **Recipe-to-Batch**: Create production batches directly from recipes
- **Cost Estimation**: Calculate recipe costs based on ingredient prices

### ✅ Sprint 2: Traceability & Costing (COMPLETED)
- **Lot Tracking**: Receive materials with lot numbers, track lot usage in batches
- **Full Traceability**: Forward trace (Lot → Batches → Orders) and backward trace (Order → Batches → Lots)
- **COGS Calculation**: Automatic cost calculation from recipes, batch profitability analysis
- **Variance Analysis**: Compare planned vs actual costs with detailed breakdowns
- **Export Reports**: Excel and CSV export for traceability and COGS reports

### ⏳ Sprint 3: Production Planning & Water (IN PROGRESS)
- **Gantt chart for production scheduling** ✅ COMPLETED
- **Tank occupancy calendar** ✅ COMPLETED
- **Water chemistry management (pH, mineral additions)** - Backend calculations ready, web UI pending
- **Yeast starter calculator** - Database schema ready, web UI pending
- **Gravity tracking (OG/FG logging)** - Quality check integration ready, dedicated dashboard pending

### 🔄 Sprint 4: Advanced Quality & Lab (PLANNED)
- Dissolved oxygen measurement logging
- Forced fermentation test tracking
- Micro plate tracking
- Sensory evaluation forms
- Statistical Process Control (SPC) charts

### 🔄 Sprint 5: Distribution & Logistics (PLANNED)
- Delivery route planning
- Driver assignment
- Proof of delivery (photo/signature)
- Vehicle temperature logging
- Return/credit management

### 🔄 Sprint 6: API & Integrations (PLANNED)
- REST API for external integrations
- Webhook support
- Accounting software integration (MISA, Fast)
- E-commerce platform sync
- POS system integration

### 🔄 Sprint 7: POS & Customer Portal (PLANNED)
- Point of Sale interface
- Customer self-service portal
- Online ordering
- Loyalty program
- QR code menu

### 🔄 Sprint 8: Analytics & Mobile (PLANNED)
- Advanced analytics dashboard
- Predictive analytics
- Mobile app (iOS/Android)
- Offline mode
- Push notifications

### 🔄 Sprint 9: Compliance & Environment (PLANNED)
- Environmental reporting
- Waste tracking
- Energy monitoring
- Regulatory compliance reports
- Audit trail

## Current Features

### Production Management
- Batch tracking with status workflow (fermenting/conditioning/completed)
- Tank management (fermenters, bright tanks)
- Production scheduling and briefings
- Quality control records
- Batch timeline and notes

### Inventory Management
- Raw materials tracking with lot numbers
- Finished goods inventory
- Low stock alerts
- Expiration tracking
- Purchase orders
- Supplier traceability

### Sales & Customers
- Customer database
- Order management
- Invoice generation (Vietnamese tax compliant)
- Sales analytics

### Accounting
- Vietnamese tax system (VAT 10%, SCT 65%, Environmental Tax)
- Chart of accounts
- Journal entries
- Financial reports (P&L, Balance Sheet)
- Invoice management

### Staff Management
- Employee database
- Role-based access control
- Task assignment
- Daily briefings

### Equipment & Maintenance
- Equipment registry
- Preventive maintenance scheduling
- Maintenance history
- Overdue alerts

### AI Agent
- Automated monitoring
- Smart alerts
- Daily reports
- Configurable rules

### Notifications
- In-app notifications
- Zalo integration (demo mode)
- Email alerts (configurable)

### Multi-language
- Vietnamese (default)
- English

## Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Authentication**: Session-based with CSRF protection
- **Scheduler**: APScheduler for background tasks

## Installation

```bash
# Clone the repository
cd brewery_manager

# Install dependencies
pip install flask flask-wtf apscheduler

# Run the application
python run.py
```

The application will be available at `http://localhost:5000`

## Default Login

- **Username**: admin
- **Password**: admin123

## Project Structure

```
brewery_manager/
├── models/
│   ├── __init__.py
│   └── database.py          # Database models and methods
├── utils/
│   ├── __init__.py
│   ├── agent.py             # AI Agent for monitoring
│   ├── auth.py              # Authentication utilities
│   ├── i18n.py              # Internationalization
│   ├── recipe_calculator.py # Recipe calculations
│   ├── scheduler.py         # Background scheduler
│   └── tax.py               # Vietnamese tax calculations
├── web/
│   ├── __init__.py
│   ├── app.py               # Flask routes
│   ├── static/              # Static assets
│   └── templates/           # HTML templates
├── translations/
│   ├── en.json              # English translations
│   └── vi.json              # Vietnamese translations
├── data/
│   └── brewery.db           # SQLite database
├── run.py                   # Application entry point
└── README.md
```

## Contributing

This is a custom-built system for Vietnamese craft breweries. For feature requests or bug reports, please contact the development team.

## License

Proprietary - All rights reserved.