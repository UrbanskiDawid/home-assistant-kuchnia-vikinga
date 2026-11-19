"""Tests for the panel response parsing (no Home Assistant needed)."""

import importlib.util
import sys
from datetime import date
from pathlib import Path

PATH = Path(__file__).parents[1] / "custom_components" / "kuchnia_vikinga" / "api.py"
spec = importlib.util.spec_from_file_location("viking_api", PATH)
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)


def test_parse_menu():
    menu = {
        "deliveryMenuMeal": [
            {
                "mealName": "Śniadanie",
                "menuMealName": "Kakaowe pancakes z twarożkiem",
                "nutrition": {"calories": 412.6, "caloriesText": "413 kcal"},
                "ingredients": [{"name": "Truskawki", "major": True}, {"name": "Kakao", "major": False}],
            },
            {"mealName": "Obiad", "menuMealName": "Zupa pomidorowa", "ingredients": None},
        ]
    }
    assert api.parse_menu(menu) == [
        {"meal": "Śniadanie", "name": "Kakaowe pancakes z twarożkiem", "kcal": 413, "ingredients": ["Truskawki", "Kakao"]},
        {"meal": "Obiad", "name": "Zupa pomidorowa", "kcal": 0, "ingredients": []},
    ]
    assert api.parse_menu({}) == []


def test_delivery_ids_filters_date_and_deleted():
    order = {
        "deliveries": [
            {"date": "2026-11-19", "deleted": False, "deliveryId": 1.2345678e7},
            {"date": "2026-11-19", "deleted": True, "deliveryId": 2},
            {"date": "2026-11-20", "deleted": False, "deliveryId": 3},
        ]
    }
    assert api.delivery_ids(order, date(2026, 11, 19)) == [12345678]
