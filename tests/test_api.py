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
                "menuMealId": 7,
                "mealName": "Śniadanie",
                "review": {"reviewId": {"menuMealId": 7}, "score": 1, "text": ""},
                "menuMealName": "Kakaowe pancakes z twarożkiem",
                "nutrition": {"calories": 412.6, "caloriesText": "413 kcal"},
                "ingredients": [{"name": "Truskawki", "major": True}, {"name": "Kakao", "major": False}],
            },
            {"menuMealId": 8, "mealName": "Obiad", "menuMealName": "Zupa pomidorowa", "ingredients": None,
             "review": None},
            {"menuMealId": 9, "mealName": "Kolacja", "menuMealName": "Sałatka", "review": {"score": 0}},
        ]
    }
    assert api.parse_menu(menu) == [
        {"id": 7, "meal": "Śniadanie", "name": "Kakaowe pancakes z twarożkiem", "kcal": 413,
         "ingredients": ["Truskawki", "Kakao"], "vote": "up"},
        {"id": 8, "meal": "Obiad", "name": "Zupa pomidorowa", "kcal": 0, "ingredients": [], "vote": None},
        {"id": 9, "meal": "Kolacja", "name": "Sałatka", "kcal": 0, "ingredients": [], "vote": "down"},
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
