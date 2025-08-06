# SIMPLE LOCATION MANAGEMENT FOR EEONAM BOT

## How to Add New Delivery Locations

1. Open file: `bot/location_manager.py`
2. Find this section at the top:

```python
# ============ SIMPLE CONFIGURATION ============
# To add new delivery locations, just add the area name to this list:
DELIVERY_LOCATIONS = [
    'Vyttila',
    'Kakkanad', 
    'Edappally',
    'Palarivattom',
    # Add new delivery areas here, separated by commas:
    # 'New Area Name',
]

# Fixed delivery charge for ALL delivery locations (change here to update all):
DELIVERY_CHARGE = 50
```

3. To add new locations, just add them to the list:

```python
DELIVERY_LOCATIONS = [
    'Vyttila',
    'Kakkanad', 
    'Edappally',
    'Palarivattom',
    'Infopark',           # ← NEW LOCATION
    'Marine Drive',       # ← NEW LOCATION
    'MG Road',           # ← NEW LOCATION
]
```

4. To change delivery charge for ALL locations:

```python
DELIVERY_CHARGE = 75  # Changed from 50 to 75
```

5. Restart the Django server after changes

## How It Works in WhatsApp

The bot will automatically show:
- **Vyttila (₹50)** [Button]
- **Kakkanad (₹50)** [Button]  
- **Edappally (₹50)** [Button]
- **Palarivattom (₹50)** [Button]
- **Infopark (₹50)** [Button]
- **Marine Drive (₹50)** [Button]
- **MG Road (₹50)** [Button]
- **Pickup Only** [Button] ← Always last

## Management Commands

```bash
# See current locations
python manage.py manage_locations --list

# Preview WhatsApp buttons
python manage.py manage_locations --whatsapp-preview

# Temporarily disable a location (without editing code)
python manage.py manage_locations --deactivate infopark_delivery

# Re-enable a location
python manage.py manage_locations --activate infopark_delivery
```

That's it! Very simple to manage.
