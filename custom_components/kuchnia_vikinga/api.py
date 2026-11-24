"""Minimal client for panel.kuchniavikinga.pl: today's meals with ingredients.

Kept free of Home Assistant imports so it can be tested on its own.
"""

from __future__ import annotations

from datetime import date

BASE_URL = "https://panel.kuchniavikinga.pl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "application/json",
    "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
    "Referer": BASE_URL + "/logowanie",
    "Origin": BASE_URL,
    "company-id": "kuchniavikinga",
    "x-launcher-type": "BROWSER_PANEL",
}


class VikingError(Exception):
    """Communication with the panel failed."""


class VikingAuthError(VikingError):
    """The panel rejected the credentials."""


SCORE_TO_VOTE = {1: "up", 0: "down"}
VOTE_TO_SCORE = {"up": 1, "down": 0}


def parse_vote(review: dict | None) -> str | None:
    """The panel's review ({score: 1|0}) as "up"/"down", or None if not voted."""
    return SCORE_TO_VOTE.get((review or {}).get("score"))


def parse_menu(menu: dict) -> list[dict]:
    """Turn a delivery menu into [{id, meal, name, kcal, ingredients, vote}]."""
    return [
        {
            "id": m.get("menuMealId"),
            "meal": m.get("mealName", ""),
            "name": m.get("menuMealName", ""),
            "kcal": round((m.get("nutrition") or {}).get("calories") or 0),
            "ingredients": [i["name"] for i in m.get("ingredients") or []],
            "vote": parse_vote(m.get("review")),
        }
        for m in menu.get("deliveryMenuMeal") or []
    ]


def delivery_ids(order: dict, day: date) -> list[int]:
    """IDs of the order's non-deleted deliveries on day (deliveryId may be a float)."""
    return [
        int(float(d["deliveryId"]))
        for d in order.get("deliveries") or []
        if not d.get("deleted") and d.get("date") == day.isoformat()
    ]


class VikingClient:
    def __init__(self, session, username: str, password: str):
        # `session` is an aiohttp.ClientSession with its own cookie jar.
        self._session = session
        self._username = username
        self._password = password

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(HEADERS)
        if method != "GET":
            # Spring CSRF: echo the XSRF-TOKEN cookie on state-changing requests.
            for cookie in self._session.cookie_jar:
                if cookie.key == "XSRF-TOKEN":
                    headers["X-XSRF-TOKEN"] = cookie.value
        return self._session.request(method, BASE_URL + path, headers=headers, **kwargs)

    async def _get_json(self, path: str):
        async with self._request("GET", path) as resp:
            if resp.status != 200:
                raise VikingError(f"GET {path}: HTTP {resp.status}")
            return await resp.json(content_type=None)

    async def login(self) -> None:
        """Replay the browser login flow; the session cookie stays in the jar."""
        for path in (
            "/logowanie",
            "/api/profile/accounts",
            "/api/open/analytical-tools-settings?companyName=kuchniavikinga&host=panel.kuchniavikinga.pl",
        ):
            async with self._request("GET", path) as resp:
                await resp.read()
        async with self._request(
            "POST",
            "/api/auth/login",
            data={"username": self._username, "password": self._password},
        ) as resp:
            if resp.status in (401, 403):
                raise VikingAuthError("Invalid username or password")
            if resp.status != 200:
                raise VikingError(f"Login failed: HTTP {resp.status}")

    async def _post_json(self, path: str, body: dict) -> None:
        async with self._request("POST", path, json=body) as resp:
            if resp.status not in (200, 201, 204):
                raise VikingError(f"POST {path}: HTTP {resp.status}")

    async def set_vote(self, menu_meal_id: int, vote: str) -> None:
        """Store a 👍/👎 for a meal on the panel (a new vote overwrites the old one)."""
        await self.login()
        try:
            await self._post_json(
                "/api/company/customer/review",
                {
                    "reviewId": {"menuMealId": menu_meal_id},
                    "score": VOTE_TO_SCORE[vote],
                    "text": "",
                },
            )
        finally:
            await self.logout()

    async def logout(self) -> None:
        try:
            async with self._request("POST", "/api/auth/logout") as resp:
                await resp.read()
        except Exception:  # noqa: BLE001
            pass

    async def todays_meals(self, day: date) -> list[dict]:
        """Log in, collect the meals delivered on day across active orders, log out."""
        await self.login()
        try:
            meals: list[dict] = []
            for order_id in await self._get_json("/api/company/customer/order/active-ids"):
                order = await self._get_json(f"/api/company/customer/order/{order_id}")
                for delivery_id in delivery_ids(order, day):
                    menu = await self._get_json(
                        f"/api/company/general/menus/delivery/{delivery_id}/new"
                    )
                    meals.extend(parse_menu(menu))
            return meals
        finally:
            await self.logout()
