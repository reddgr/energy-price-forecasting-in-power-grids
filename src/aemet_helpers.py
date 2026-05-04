import requests
import pandas as pd
from datetime import datetime
from typing import Optional


DEFAULT_BASE_URL = "https://opendata.aemet.es/opendata/api"


class AemetClient:
    """Lightweight client for AEMET OpenData API.

    Example:
        client = AemetClient(api_key="MY_KEY")
        datos_url = client._get_data_url("observacion/convencional/todas")
        observations = client._download_json(datos_url)
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, session: Optional[requests.Session] = None):
        if not api_key:
            raise ValueError("api_key is required for AemetClient")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        # Use header named by AEMET API for key-based auth
        self.session.headers.update({"api_key": self.api_key})

    def _get_data_url(self, endpoint: str, params: dict | None = None) -> str | None:
        resp = self.session.get(f"{self.base_url}/{endpoint.lstrip('/')}", params=params)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("datos")

    def _download_json(self, url: str):
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def fetch_metadata(self, endpoint: str) -> tuple[dict, pd.DataFrame]:
        resp = self.session.get(f"{self.base_url}/{endpoint.lstrip('/')}")
        resp.raise_for_status()
        meta_url = resp.json().get("metadatos")
        if not meta_url:
            return {}, pd.DataFrame()
        metadata = self._download_json(meta_url)
        return metadata

    def fetch_station_history(self, idema: str, start_date: str, end_date: str):
        date_format = "%Y-%m-%d"
        for label, value in (("start_date", start_date), ("end_date", end_date)):
            try:
                datetime.strptime(value, date_format)
            except ValueError as exc:
                raise ValueError(f"{label} must use 'YYYY-MM-DD' format.") from exc

        endpoint = (
            f"valores/climatologicos/diarios/datos/fechaini/"
            f"{start_date}T00:00:00UTC/fechafin/{end_date}T00:00:00UTC/estacion/{idema}"
        )

        meta_resp = self.session.get(f"{self.base_url}/{endpoint}")
        meta_resp.raise_for_status()
        datos_url = meta_resp.json().get("datos")
        if not datos_url:
            raise ValueError("No datos URL returned by API")

        datos_resp = self.session.get(datos_url)
        datos_resp.raise_for_status()
        return datos_resp.json()


__all__ = ["AemetClient", "DEFAULT_BASE_URL"]