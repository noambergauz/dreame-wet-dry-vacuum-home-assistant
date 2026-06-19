"""Persistent MQTT client for the Dreame wet & dry vacuum real-time state.

The device publishes property changes to the Dreame MQTT broker (the device's
bindDomain). We subscribe to /status/{did}/{uid}/{model}/eu/ and maintain a
live dict of {(siid, piid): value}. Commands/RPC are NOT supported by this
model, so this client is receive-only.
"""
from __future__ import annotations

import json
import logging
import random
import ssl
import threading
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class DreameMqttClient:
    """Receive-only MQTT client maintaining the device's live property state."""

    def __init__(
        self,
        uid: str,
        access_token: str,
        device_id: str,
        model: str,
        bind_domain: str,
        on_update: Callable[[dict[tuple[int, int], Any]], None],
        region: str = "eu",
    ) -> None:
        self._uid = uid
        self._token = access_token
        self._did = device_id
        self._model = model
        host, _, port = bind_domain.partition(":")
        self._host = host
        self._port = int(port or 19973)
        self._region = region
        self._on_update = on_update
        self._client: mqtt.Client | None = None
        self._thread: threading.Thread | None = None
        self.state: dict[tuple[int, int], Any] = {}
        self.connected = False

    @property
    def topic(self) -> str:
        return f"/status/{self._did}/{self._uid}/{self._model}/{self._region}/"

    def update_token(self, access_token: str) -> None:
        """Refresh the token used as MQTT password (call before reconnecting)."""
        self._token = access_token

    def start(self) -> None:
        cid = "p_" + "".join(random.choices("0123456789abcdef", k=16))
        client = mqtt.Client(client_id=cid, protocol=mqtt.MQTTv311)
        client.username_pw_set(self._uid, self._token)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.reconnect_delay_set(min_delay=5, max_delay=120)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        self._client = client
        client.connect_async(self._host, self._port, keepalive=60)
        client.loop_start()
        _LOGGER.debug("Dreame MQTT client started for %s", self._did)

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            try:
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self.connected = True
            client.subscribe(self.topic)
            _LOGGER.info("Dreame MQTT connected, subscribed %s", self.topic)
        else:
            _LOGGER.warning("Dreame MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self.connected = False
        _LOGGER.debug("Dreame MQTT disconnected rc=%s", rc)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = msg.payload.decode("utf-8", "replace")
            data = json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            return
        params = data.get("data", {}).get("params") or data.get("params") or []
        changed: dict[tuple[int, int], Any] = {}
        for item in params:
            if isinstance(item, dict) and "siid" in item and "piid" in item:
                key = (item["siid"], item["piid"])
                self.state[key] = item.get("value")
                changed[key] = item.get("value")
        if changed:
            try:
                self._on_update(dict(self.state))
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error in MQTT update callback")
