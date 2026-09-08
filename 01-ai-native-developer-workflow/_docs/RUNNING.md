# Running the Household Chore Manager

## Setup

### 1. Install Dependencies
The project requires Django 6.1. It should already be installed, but you can verify:
```bash
pip install django
```

### 2. Database Migrations
The database has been set up with migrations already applied. To verify everything is ready:
```bash
python manage.py check
```

### 3. Create a Superuser (Optional)
To access the Django admin interface at `/admin/`:
```bash
python manage.py createsuperuser
```

## Running the Development Server

Start the development server:
```bash
python manage.py runserver
```

The application will be available at:
- **Main App**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin/

## Using the Chore Manager

### Main Interface
- **View Chores**: http://localhost:8000/ - See all pending and completed chores
- **Add Chore**: http://localhost:8000/add/ - Add a new chore with description and priority
- **Complete Chore**: Click "✓ Complete" on any pending chore, enter your name, and mark it done

### Features
- **Priority Levels**: High, Medium, Low
- **Chore Status**: Pending or Completed
- **Completion Tracking**: Records who completed it and when
- **Network Access**: Accessible from any device on the home network

## Architecture

### Models
- **Chore**: Main model with description, priority, status, timestamps, and completion info

### Views
- `chore_list`: Displays all chores separated by status
- `add_chore`: Form to add new chores
- `complete_chore`: Form to mark chore as complete with name entry

### Templates
- `base.html`: Main layout with responsive design
- `chore_list.html`: Chore display page
- `add_chore.html`: Add chore form
- `complete_chore.html`: Complete chore form

## Database

SQLite database is stored in `db.sqlite3`. To reset the database:
```bash
rm db.sqlite3
python manage.py migrate
```

## Accessing from Other Devices on the Network

To access the app from other devices on your home network, run:
```bash
python manage.py runserver 0.0.0.0:8000
```

Then access it using your computer's IP address, e.g., `http://192.168.1.100:8000/`

## Notes
- No authentication required - anyone on the network can access
- Anyone can add chores and mark them complete
- Completed chores are kept in history for reference
