"""Portal regions and linked blocks that teleport players or send them to another server."""

import time

from endstone import ColorFormat, Player
from endstone.event import PlayerInteractEvent
from endstone.level import Location
from endstone.plugin import Plugin

from endstone_chaosportals.store import JsonStore

COOLDOWN_SECONDS = 3.0
DEFAULT_RADIUS = 1.5
DEFAULT_PORT = 19132
REGION_HEIGHT = 3


class PortalManager:
    def __init__(self, plugin: Plugin, store: JsonStore, hub_store: JsonStore) -> None:
        self.plugin = plugin
        self.store = store
        self.hub_store = hub_store
        self.portals = store.data
        self.arming: dict[str, str] = {}  # player name -> portal waiting for a block click
        self.cooldown: dict[str, float] = {}
        self.inside: dict[str, str] = {}

    def _use(self, player: Player, name: str) -> None:
        now = time.monotonic()
        if now - self.cooldown.get(player.name, 0.0) < COOLDOWN_SECONDS:
            return
        self.cooldown[player.name] = now
        target = self.portals[name].get("target")
        if target is None:
            player.send_error_message(f"Portal {name} hat noch kein Ziel.")
        else:
            self._travel(player, target)

    def _travel(self, player: Player, target: dict) -> None:
        if target["type"] == "server":
            player.transfer(target["host"], target["port"])
            return
        dimension = self.plugin.server.level.get_dimension(target["dim"])
        player.teleport(
            Location(dimension, target["x"], target["y"], target["z"], target["pitch"], target["yaw"])
        )

    def hub(self, player: Player) -> bool:
        target = self.hub_store.data.get("target")
        if target is None:
            player.send_error_message("Auf diesem Server ist noch kein Hub gesetzt.")
            return False
        self._travel(player, target)
        return True

    @staticmethod
    def _here(player: Player) -> dict:
        loc = player.location
        return {
            "type": "tp", "dim": player.dimension.name, "x": loc.x, "y": loc.y, "z": loc.z,
            "pitch": loc.pitch, "yaw": loc.yaw,
        }

    def _set_hub(self, player: Player, args: list[str]) -> bool:
        if args:
            port = int(args[1]) if len(args) > 1 else DEFAULT_PORT
            self.hub_store.data["target"] = {"type": "server", "host": args[0], "port": port}
            player.send_message(f"{ColorFormat.GREEN}/hub führt jetzt zu {args[0]}:{port}.")
        else:
            self.hub_store.data["target"] = self._here(player)
            player.send_message(f"{ColorFormat.GREEN}/hub führt jetzt zu deinem Standort.")
        self.hub_store.save()
        return True

    def _portal_at(self, player: Player) -> str | None:
        loc = player.location
        for name, portal in self.portals.items():
            region = portal.get("region")
            if region is None or region["dim"] != player.dimension.name:
                continue
            dx, dz = loc.x - region["x"], loc.z - region["z"]
            if dx * dx + dz * dz <= region["radius"] ** 2 and 0 <= loc.y - region["y"] < REGION_HEIGHT:
                return name
        return None

    def tick(self) -> None:
        for player in self.plugin.server.online_players:
            hit = self._portal_at(player)
            if hit is None:
                self.inside.pop(player.name, None)
            elif hit != self.inside.get(player.name):
                self.inside[player.name] = hit
                self._use(player, hit)

    def on_interact(self, event: PlayerInteractEvent) -> None:
        if event.action != PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK or not event.has_block:
            return
        player, block = event.player, event.block
        key = f"{block.dimension.name}:{block.x}:{block.y}:{block.z}"
        armed = self.arming.pop(player.name, None)
        if armed is not None:
            self.portals[armed].setdefault("signs", []).append(key)
            self.store.save()
            event.cancelled = True
            self.cooldown[player.name] = time.monotonic()
            player.send_message(f"{ColorFormat.GREEN}Block mit Portal {armed} verknüpft.")
            return
        for name, portal in self.portals.items():
            if key in portal.get("signs", []):
                event.cancelled = True
                self._use(player, name)
                return

    def on_quit(self, player: Player) -> None:
        self.arming.pop(player.name, None)
        self.inside.pop(player.name, None)

    def command(self, player: Player, args: list[str]) -> bool:
        action = args[0]
        if action == "list":
            return self._list(player)
        if action == "sethub":
            return self._set_hub(player, args[1:])
        name = args[1]
        if action == "create":
            self._create(player, name, float(args[2]) if len(args) > 2 else DEFAULT_RADIUS)
        elif action == "sign":
            self.portals.setdefault(name, {})
            self.arming[player.name] = name
            player.send_message("Klicke jetzt mit Rechtsklick auf das Schild.")
        elif name not in self.portals:
            player.send_error_message("Unbekanntes Portal.")
            return False
        elif action == "target":
            self._set_target(player, name)
        elif action == "server":
            port = int(args[3]) if len(args) > 3 else DEFAULT_PORT
            self.portals[name]["target"] = {"type": "server", "host": args[2], "port": port}
            player.send_message(f"{ColorFormat.GREEN}{name} führt jetzt zu {args[2]}:{port}.")
        elif action == "remove":
            del self.portals[name]
            player.send_message(f"{ColorFormat.GREEN}Portal {name} entfernt.")
        self.store.save()
        return True

    def _list(self, player: Player) -> bool:
        for name, portal in self.portals.items():
            player.send_message(
                f"{name}: Ziel {portal.get('target')}, "
                f"Bereich {portal.get('region') is not None}, {len(portal.get('signs', []))} Schilder"
            )
        if not self.portals:
            player.send_message("Keine Portale vorhanden.")
        return True

    def _create(self, player: Player, name: str, radius: float) -> None:
        loc = player.location
        self.portals.setdefault(name, {})["region"] = {
            "dim": player.dimension.name, "x": loc.x, "y": loc.y, "z": loc.z, "radius": radius,
        }
        self.inside[player.name] = name
        player.send_message(f"{ColorFormat.GREEN}Portal {name} steht hier. Jetzt /portal target oder server.")

    def _set_target(self, player: Player, name: str) -> None:
        self.portals[name]["target"] = self._here(player)
        player.send_message(f"{ColorFormat.GREEN}Ziel von {name} ist jetzt dein Standort.")
