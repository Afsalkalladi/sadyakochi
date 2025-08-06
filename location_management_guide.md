# EeOnam Bot Location Management Guide

## Overview
The EeOnam WhatsApp bot uses a simple configuration system for delivery locations. All delivery locations have the same delivery charge, and adding new locations is as easy as adding to a list.

## Simple Configuration

### Location Settings (in `bot/location_manager.py`)

```python
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

## Quick Management Tasks

### 1. Adding New Delivery Locations

Simply edit the `DELIVERY_LOCATIONS` list in `bot/location_manager.py`:

```python
DELIVERY_LOCATIONS = [
    'Vyttila',
    'Kakkanad', 
    'Edappally',
    'Palarivattom',
    'Infopark',        # ← New location added
    'Marine Drive',    # ← Another new location
]
```

### 2. Change Delivery Charge for All Locations

Update the `DELIVERY_CHARGE` value:

```python
DELIVERY_CHARGE = 60  # Changed from 50 to 60 for all delivery locations
```

### 3. Temporarily Disable a Location

```python
# In Django shell or management command
from bot.location_manager import location_manager
location_manager.deactivate_location('vyttila_delivery')
```

## Current Setup

### Active Locations
- **Vyttila (Delivery)** - ₹50 delivery fee
- **Kakkanad (Delivery)** - ₹50 delivery fee
- **Edappally (Delivery)** - ₹50 delivery fee
- **Palarivattom (Delivery)** - ₹50 delivery fee
- **Pickup Only** - ₹0 fee

### WhatsApp Button Order
1. All delivery locations with fees (e.g., "Vyttila (₹50)")
2. Pickup Only (at the end)

## Advanced Management

### Via Django Shell

```bash
python manage.py shell
```

```python
from bot.location_manager import location_manager

# View all locations
for loc_id, location in location_manager.get_all_locations().items():
    print(f"{location.name}: ₹{location.delivery_fee} ({'Active' if location.is_active else 'Inactive'})")

# Update all delivery fees at once
location_manager.update_all_delivery_fees(75)

# Check specific location
if location_manager.is_valid_location('vyttila_delivery'):
    print("Vyttila delivery is available")
```

## Management Command

Use the Django management command for easy location management:

```bash
# List all locations
python manage.py manage_locations --list

# Preview WhatsApp buttons
python manage.py manage_locations --whatsapp-preview

# Show location statistics
python manage.py manage_locations --stats

# Temporarily disable a location
python manage.py manage_locations --deactivate vyttila_delivery

# Re-activate a location
python manage.py manage_locations --activate vyttila_delivery
```

## Best Practices

1. **Always test location changes** in development before production
2. **Restart the Django server** after changing `DELIVERY_LOCATIONS` or `DELIVERY_CHARGE`
3. **Keep delivery fees competitive** but profitable
4. **Communicate changes** to customers proactively

## Emergency Procedures

### Disable All Delivery During Issues

```python
# In Django shell - temporarily disable all delivery, keep only pickup
from bot.location_manager import location_manager
for location_id in location_manager.get_delivery_locations().keys():
    location_manager.deactivate_location(location_id)
```

### Update Delivery Charge for All Locations

```python
# Update the DELIVERY_CHARGE in bot/location_manager.py, then:
from bot.location_manager import location_manager
location_manager.update_all_delivery_fees(75)  # New fee for all delivery locations
```

This simple location management system makes it easy to add new delivery areas and maintain consistent pricing across all locations.
