from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import PlayerInteractEvent, PlayerQuitEvent, event_handler
from endstone.plugin import Plugin

from endstone_chaosportals.portals import PortalManager
from endstone_chaosportals.store import JsonStore


class ChaosPortalsPlugin(Plugin):
    prefix = "ChaosPortals"
    api_version = "0.11"

    commands = {
        "portal": {
            "description": "Portals and signs that teleport players or send them to another server",
            "usages": [
                "/portal (create)<action: PortalCreateAction> <name: str> [radius: float]",
                "/portal (sign|target|remove)<action: PortalNameAction> <name: str>",
                "/portal (server)<action: PortalServerAction> <name: str> <host: str> [port: int]",
                "/portal (list)<action: PortalListAction>",
            ],
            "permissions": ["chaosportals.command"],
        },
    }
    permissions = {
        "chaosportals.command": {"description": "Manage portals and signs", "default": "op"},
    }

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.manager = PortalManager(self, JsonStore(self.data_folder / "portals.json"))
        self.server.scheduler.run_task(self, self.manager.tick, delay=5, period=5)
        self.register_events(self)

    def on_disable(self) -> None:
        self.manager.store.save()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("Nur Spieler können diesen Befehl nutzen.")
            return False
        return self.manager.command(sender, args)

    @event_handler
    def on_interact(self, event: PlayerInteractEvent) -> None:
        self.manager.on_interact(event)

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        self.manager.on_quit(event.player)
