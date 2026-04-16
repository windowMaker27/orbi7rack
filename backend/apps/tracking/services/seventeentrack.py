import httpx
from django.conf import settings


class SeventeentrackClient:
    BASE_URL = "https://api.17track.net/track/v1"

    def __init__(self):
        self.headers = {
            "17token": settings.SEVENTEENTRACK_API_KEY,
            "Content-Type": "application/json",
        }

    def register(self, tracking_number: str, carrier: int | None = None, tag: str = ""):
        payload = [{"number": tracking_number, "tag": tag}]
        if carrier:
            payload[0]["carrier"] = carrier

        response = httpx.post(
            f"{self.BASE_URL}/register",
            headers=self.headers,
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    def get_track_info(self, tracking_number: str, carrier: int | None = None):
        payload = [{"number": tracking_number}]
        if carrier:
            payload[0]["carrier"] = carrier

        response = httpx.post(
            f"{self.BASE_URL}/gettrackinfo",
            headers=self.headers,
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()