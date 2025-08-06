"""
Location management for EeOnam bot
Simple configuration for delivery locations and pricing
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


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

# ============ END CONFIGURATION ============


@dataclass
class DeliveryLocation:
    """Represents a delivery location with its properties"""
    id: str
    name: str
    display_name: str
    delivery_fee: int
    is_active: bool = True
    description: str = ""


class LocationManager:
    """Manages all delivery locations and related operations"""
    
    def __init__(self):
        self._locations = self._initialize_locations()
    
    def _initialize_locations(self) -> Dict[str, DeliveryLocation]:
        """Initialize all available locations from simple configuration"""
        locations = {}
        
        # Add all delivery locations from the list
        for area_name in DELIVERY_LOCATIONS:
            location_id = f"{area_name.lower().replace(' ', '_')}_delivery"
            locations[location_id] = DeliveryLocation(
                id=location_id,
                name=area_name,
                display_name=f"{area_name} (Delivery)",
                delivery_fee=DELIVERY_CHARGE,
                description=f'Delivery to {area_name} area'
            )
        
        # Add pickup option
        locations['pickup'] = DeliveryLocation(
            id='pickup',
            name='Pickup Only',
            display_name='Pickup Only',
            delivery_fee=0,
            description='Customer pickup at our location'
        )
        
        return locations
    
    def get_all_locations(self) -> Dict[str, DeliveryLocation]:
        """Get all locations"""
        return self._locations
    
    def get_active_locations(self) -> Dict[str, DeliveryLocation]:
        """Get only active locations"""
        return {k: v for k, v in self._locations.items() if v.is_active}
    
    def get_delivery_locations(self) -> Dict[str, DeliveryLocation]:
        """Get only delivery locations (excluding pickup)"""
        return {k: v for k, v in self._locations.items() 
                if v.is_active and 'delivery' in v.id}
    
    def get_location(self, location_id: str) -> DeliveryLocation:
        """Get a specific location by ID"""
        return self._locations.get(location_id)
    
    def is_valid_location(self, location_id: str) -> bool:
        """Check if location ID is valid and active"""
        location = self.get_location(location_id)
        return location is not None and location.is_active
    
    def get_delivery_fee(self, location_id: str) -> int:
        """Get delivery fee for a location"""
        location = self.get_location(location_id)
        return location.delivery_fee if location else 0
    
    def get_display_name(self, location_id: str) -> str:
        """Get display name for a location"""
        location = self.get_location(location_id)
        return location.display_name if location else "Unknown Location"
    
    def is_delivery_location(self, location_id: str) -> bool:
        """Check if location requires delivery"""
        return 'delivery' in location_id
    
    def get_junction_choices(self) -> List[Tuple[str, str]]:
        """Get choices for Django model field"""
        return [(loc.id, loc.display_name) for loc in self.get_active_locations().values()]
    
    def get_whatsapp_buttons(self, max_buttons: int = 3) -> List[List[Dict]]:
        """Get WhatsApp interactive buttons for locations (delivery locations first, then pickup)"""
        delivery_locations = list(self.get_delivery_locations().values())
        pickup_locations = [loc for loc in self.get_active_locations().values() 
                          if not self.is_delivery_location(loc.id)]
        
        # Order: delivery locations first, then pickup
        ordered_locations = delivery_locations + pickup_locations
        
        # Split into groups for WhatsApp (max 3 buttons per message)
        button_groups = []
        current_group = []
        
        for location in ordered_locations:
            if len(current_group) >= max_buttons:
                button_groups.append(current_group)
                current_group = []
            
            button_text = f"{location.name}"
            if location.delivery_fee > 0:
                button_text += f" (₹{location.delivery_fee})"
            
            current_group.append({
                "type": "reply",
                "reply": {
                    "id": location.id,
                    "title": button_text[:20]  # WhatsApp button title limit
                }
            })
        
        if current_group:
            button_groups.append(current_group)
        
        return button_groups
    
    def get_location_summary_text(self) -> str:
        """Get formatted text summary of all locations"""
        delivery_locations = self.get_delivery_locations()
        pickup_locations = {k: v for k, v in self.get_active_locations().items() 
                          if not self.is_delivery_location(k)}
        
        text = ""
        
        if delivery_locations:
            text += "*Delivery Locations*:\n"
            for location in delivery_locations.values():
                fee_text = f"₹{location.delivery_fee} delivery fee" if location.delivery_fee > 0 else "Free delivery"
                text += f"• {location.name} ({fee_text})\n"
            text += "\n"
        
        if pickup_locations:
            text += "*Pickup Locations*:\n"
            for location in pickup_locations.values():
                text += f"• {location.name} (No extra fee)\n"
        
        return text
    
    def add_location(self, location: DeliveryLocation):
        """Add a new location (for future expansion)"""
        self._locations[location.id] = location
    
    def deactivate_location(self, location_id: str):
        """Deactivate a location without removing it"""
        if location_id in self._locations:
            self._locations[location_id].is_active = False
    
    def activate_location(self, location_id: str):
        """Activate a location"""
        if location_id in self._locations:
            self._locations[location_id].is_active = True
    
    def update_delivery_fee(self, location_id: str, new_fee: int):
        """Update delivery fee for a location"""
        if location_id in self._locations:
            self._locations[location_id].delivery_fee = new_fee
    
    def update_all_delivery_fees(self, new_fee: int):
        """Update delivery fee for all delivery locations at once"""
        global DELIVERY_CHARGE
        DELIVERY_CHARGE = new_fee
        
        for location_id, location in self._locations.items():
            if self.is_delivery_location(location_id):
                location.delivery_fee = new_fee


# Global location manager instance
location_manager = LocationManager()
