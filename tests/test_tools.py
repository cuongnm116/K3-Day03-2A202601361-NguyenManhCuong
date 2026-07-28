from src.tools.tools import calc_shipping, check_stock, get_discount


def test_check_stock_returns_catalog_data():
    result = check_stock("iPhone")

    assert result == {
        "item_name": "iPhone",
        "price": 25_000_000,
        "stock": 15,
        "weight_kg": 0.4,
        "ok": True,
        "status": "in_stock",
    }


def test_check_stock_reports_not_found_without_crashing():
    result = check_stock("AirPods")

    assert result["ok"] is False
    assert result["error"] == "item_not_found"
    assert "AirPods" in result["message"]


def test_check_stock_reports_missing_argument():
    result = check_stock()

    assert result["ok"] is False
    assert result["error"] == "invalid_input"


def test_out_of_stock_product_has_explicit_status():
    result = check_stock("MacBook")

    assert result["ok"] is True
    assert result["stock"] == 0
    assert result["status"] == "out_of_stock"


def test_get_discount_handles_valid_and_expired_codes():
    valid = get_discount("winner")
    expired = get_discount("LEGACY")

    assert valid["valid"] is True
    assert valid["discount_percent"] == 10
    assert expired["valid"] is False
    assert expired["discount_percent"] == 0


def test_get_discount_reports_unknown_and_missing_codes():
    unknown = get_discount("UNKNOWN")
    missing = get_discount()

    assert unknown["error"] == "coupon_not_found"
    assert missing["error"] == "invalid_input"


def test_calc_shipping_returns_expected_hanoi_cost():
    result = calc_shipping(weight=0.8, destination="Hanoi")

    assert result["ok"] is True
    assert result["shipping_cost"] == 38_000
    assert result["estimated_days"] == 1


def test_calc_shipping_validates_each_argument():
    assert calc_shipping(destination="Hanoi")["error"] == "invalid_input"
    assert calc_shipping(weight=0.8)["error"] == "invalid_input"
    assert calc_shipping(weight=-1, destination="Hanoi")["error"] == "invalid_input"
    assert (
        calc_shipping(weight=0.8, destination="Quang Ninh")["error"]
        == "unsupported_destination"
    )


def test_tools_are_deterministic_and_do_not_expose_mutable_source_data():
    first = check_stock("iPad")
    second = check_stock("iPad")

    assert first == second
    first["stock"] = 0
    assert check_stock("iPad")["stock"] == 8
    assert get_discount("WINNER") == get_discount("WINNER")
    assert calc_shipping(0.5, "Saigon") == calc_shipping(0.5, "Saigon")


def test_extended_catalog_contains_available_and_out_of_stock_products():
    phone = check_stock("Samsung Galaxy S24")
    console = check_stock("PlayStation 5")

    assert phone["price"] == 22_990_000
    assert phone["status"] == "in_stock"
    assert console["stock"] == 0
    assert console["status"] == "out_of_stock"


def test_extended_coupons_cover_valid_and_expired_promotions():
    vip = get_discount("vip20")
    expired = get_discount("EXPIRED2025")

    assert vip["valid"] is True
    assert vip["discount_percent"] == 20
    assert expired["valid"] is False
    assert expired["discount_percent"] == 0


def test_extended_shipping_zones_support_accented_and_plain_aliases():
    accented = calc_shipping(1.0, "Đà Nẵng")
    plain = calc_shipping(1.0, "da nang")

    assert accented == plain
    assert accented["destination"] == "Da Nang"
    assert accented["shipping_cost"] == 38_000
