from copy import deepcopy
from typing import Any, Dict, Optional


CATALOG: Dict[str, Dict[str, Any]] = {
    "iphone": {
        "item_name": "iPhone",
        "price": 25_000_000,
        "stock": 15,
        "weight_kg": 0.4,
    },
    "ipad": {
        "item_name": "iPad",
        "price": 18_000_000,
        "stock": 8,
        "weight_kg": 0.5,
    },
    "macbook": {
        "item_name": "MacBook",
        "price": 35_000_000,
        "stock": 0,
        "weight_kg": 2.0,
    },
    "airpods pro": {
        "item_name": "AirPods Pro",
        "price": 5_990_000,
        "stock": 24,
        "weight_kg": 0.06,
    },
    "apple watch": {
        "item_name": "Apple Watch",
        "price": 10_990_000,
        "stock": 12,
        "weight_kg": 0.3,
    },
    "samsung galaxy s24": {
        "item_name": "Samsung Galaxy S24",
        "price": 22_990_000,
        "stock": 18,
        "weight_kg": 0.4,
    },
    "google pixel 9": {
        "item_name": "Google Pixel 9",
        "price": 20_490_000,
        "stock": 6,
        "weight_kg": 0.4,
    },
    "dell xps 13": {
        "item_name": "Dell XPS 13",
        "price": 32_990_000,
        "stock": 4,
        "weight_kg": 1.2,
    },
    "asus rog zephyrus": {
        "item_name": "ASUS ROG Zephyrus",
        "price": 44_990_000,
        "stock": 3,
        "weight_kg": 2.1,
    },
    "sony wh-1000xm5": {
        "item_name": "Sony WH-1000XM5",
        "price": 8_490_000,
        "stock": 10,
        "weight_kg": 0.5,
    },
    "nintendo switch oled": {
        "item_name": "Nintendo Switch OLED",
        "price": 8_990_000,
        "stock": 7,
        "weight_kg": 0.7,
    },
    "playstation 5": {
        "item_name": "PlayStation 5",
        "price": 13_990_000,
        "stock": 0,
        "weight_kg": 6.7,
    },
}

COUPONS: Dict[str, Dict[str, Any]] = {
    "WINNER": {"discount_percent": 10, "valid": True},
    "LEGACY": {"discount_percent": 0, "valid": False},
    "NEWUSER": {"discount_percent": 12, "valid": True},
    "SUMMER15": {"discount_percent": 15, "valid": True},
    "SAVE5": {"discount_percent": 5, "valid": True},
    "VIP20": {"discount_percent": 20, "valid": True},
    "STUDENT10": {"discount_percent": 10, "valid": True},
    "EXPIRED2025": {"discount_percent": 0, "valid": False},
    "BLACKFRIDAY": {"discount_percent": 0, "valid": False},
}

SHIPPING_ZONES: Dict[str, Dict[str, Any]] = {
    "hanoi": {"destination": "Hanoi", "base_cost": 30_000, "estimated_days": 1},
    "ha noi": {"destination": "Hanoi", "base_cost": 30_000, "estimated_days": 1},
    "hà nội": {"destination": "Hanoi", "base_cost": 30_000, "estimated_days": 1},
    "saigon": {"destination": "Saigon", "base_cost": 25_000, "estimated_days": 2},
    "sài gòn": {"destination": "Saigon", "base_cost": 25_000, "estimated_days": 2},
    "ho chi minh city": {
        "destination": "Saigon",
        "base_cost": 25_000,
        "estimated_days": 2,
    },
    "ho chi minh": {
        "destination": "Saigon",
        "base_cost": 25_000,
        "estimated_days": 2,
    },
    "hcm": {
        "destination": "Saigon",
        "base_cost": 25_000,
        "estimated_days": 2,
    },
    "da nang": {
        "destination": "Da Nang",
        "base_cost": 28_000,
        "estimated_days": 2,
    },
    "đà nẵng": {
        "destination": "Da Nang",
        "base_cost": 28_000,
        "estimated_days": 2,
    },
    "hai phong": {
        "destination": "Hai Phong",
        "base_cost": 32_000,
        "estimated_days": 2,
    },
    "hải phòng": {
        "destination": "Hai Phong",
        "base_cost": 32_000,
        "estimated_days": 2,
    },
    "can tho": {
        "destination": "Can Tho",
        "base_cost": 35_000,
        "estimated_days": 3,
    },
    "cần thơ": {
        "destination": "Can Tho",
        "base_cost": 35_000,
        "estimated_days": 3,
    },
    "hue": {
        "destination": "Hue",
        "base_cost": 31_000,
        "estimated_days": 3,
    },
    "huế": {
        "destination": "Hue",
        "base_cost": 31_000,
        "estimated_days": 3,
    },
    "nha trang": {
        "destination": "Nha Trang",
        "base_cost": 33_000,
        "estimated_days": 3,
    },
    "da lat": {
        "destination": "Da Lat",
        "base_cost": 36_000,
        "estimated_days": 3,
    },
    "đà lạt": {
        "destination": "Da Lat",
        "base_cost": 36_000,
        "estimated_days": 3,
    },
    "vung tau": {
        "destination": "Vung Tau",
        "base_cost": 30_000,
        "estimated_days": 2,
    },
    "vũng tàu": {
        "destination": "Vung Tau",
        "base_cost": 30_000,
        "estimated_days": 2,
    },
}


def _error(error: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "error": error, "message": message}


def check_stock(item_name: Optional[str] = None) -> Dict[str, Any]:
    """Return current catalog data for one product. This tool is read-only."""
    if not isinstance(item_name, str) or not item_name.strip():
        return _error("invalid_input", "item_name is required and must be a string")

    item = CATALOG.get(item_name.strip().casefold())
    if item is None:
        return _error("item_not_found", f"Item '{item_name}' was not found")

    result = deepcopy(item)
    result.update(
        {
            "ok": True,
            "status": "in_stock" if result["stock"] > 0 else "out_of_stock",
        }
    )
    return result


def get_discount(coupon_code: Optional[str] = None) -> Dict[str, Any]:
    """Validate one coupon code. This tool is read-only."""
    if not isinstance(coupon_code, str) or not coupon_code.strip():
        return _error(
            "invalid_input", "coupon_code is required and must be a string"
        )

    normalized_code = coupon_code.strip().upper()
    coupon = COUPONS.get(normalized_code)
    if coupon is None:
        return _error(
            "coupon_not_found", f"Coupon '{normalized_code}' was not found"
        )

    return {
        "ok": True,
        "coupon_code": normalized_code,
        **deepcopy(coupon),
    }


def calc_shipping(
    weight: Optional[float] = None, destination: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate deterministic shipping cost. This tool has no side effects."""
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        return _error("invalid_input", "weight is required and must be a number")
    if weight <= 0:
        return _error("invalid_input", "weight must be greater than zero")
    if not isinstance(destination, str) or not destination.strip():
        return _error(
            "invalid_input", "destination is required and must be a string"
        )

    zone = SHIPPING_ZONES.get(destination.strip().casefold())
    if zone is None:
        return _error(
            "unsupported_destination",
            f"Shipping to '{destination}' is not supported",
        )

    shipping_cost = zone["base_cost"] + round(float(weight) * 10_000)
    return {
        "ok": True,
        "destination": zone["destination"],
        "weight": float(weight),
        "shipping_cost": shipping_cost,
        "estimated_days": zone["estimated_days"],
    }


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "check_stock": {
        "name": "check_stock",
        "description": "Check product price, stock, status, and unit weight.",
        "parameters": {"item_name": "string, required"},
        "function": check_stock,
    },
    "get_discount": {
        "name": "get_discount",
        "description": "Validate a coupon and return its discount percentage.",
        "parameters": {"coupon_code": "string, required"},
        "function": get_discount,
    },
    "calc_shipping": {
        "name": "calc_shipping",
        "description": "Calculate shipping cost and estimated delivery days.",
        "parameters": {
            "weight": "positive number, required",
            "destination": "string, required",
        },
        "function": calc_shipping,
    },
}
