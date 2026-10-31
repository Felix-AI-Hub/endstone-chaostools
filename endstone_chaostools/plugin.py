from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import PlayerInteractEvent, PlayerJoinEvent, PlayerQuitEvent, event_handler
from endstone.plugin import Plugin

from endstone_chaostools.portals import PortalManager
from endstone_chaostools.store import JsonStore
from endstone_chaostools.texts import TextManager


class ChaosToolsPlugin(Plugin):
    prefix = "ChaosTools"
    api_version = "0.11"

    commands = {
        "ft": {
            "description": "Floating texts: create, move with the crosshair, edit, remove",
            "usages": [
                "/ft (create)<action: FtCreateAction> <text: message>",
                "/ft (edit)<action: FtEditAction> <id: str> <text: message>",
                "/ft (dist)<action: FtDistAction> <blocks: float>",
                "/ft (list|drop)<action: FtSimpleAction>",
                "/ft (move|remove)<action: FtPickAction> [id: str]",
            ],
            "permissions": ["chaostools.command"],
        },
        "portal": {
            "description": "Portals and signs that teleport players or send them to another server",
            "usages": [
                "/portal (create)<action: PortalCreateAction> <name: str> [radius: float]",
                "/portal (sign|target|remove)<action: PortalNameAction> <name: str>",
                "/portal (server)<action: PortalServerAction> <name: str> <host: str> [port: int]",
                "/portal (list)<action: PortalListAction>",
            ],
            "permissions": ["chaostools.command"],
        },
    }
    permissions = {
        "chaostools.command": {"description": "Manage floating texts and portals", "default": "op"},
    }

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.texts = TextManager(self, JsonStore(self.data_folder / "texts.json"))
        self.portals = PortalManager(self, JsonStore(self.data_folder / "portals.json"))
        self.register_events(self)
        scheduler = self.server.scheduler
        scheduler.run_task(self, self.texts.tick_moving, delay=1, period=1)
        scheduler.run_task(self, self.texts.sync, delay=20, period=20)
        scheduler.run_task(self, self.portals.tick, delay=5, period=5)

    def on_disable(self) -> None:
        self.texts.store.save()
        self.portals.store.save()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("Nur Spieler können diesen Befehl nutzen.")
            return False
        if command.name == "ft":
            return self.texts.command(sender, args)
        return self.portals.command(sender, args)

    @event_handler
    def on_interact(self, event: PlayerInteractEvent) -> None:
        self.portals.on_interact(event)

    @event_handler
    def on_join(self, event: PlayerJoinEvent) -> None:
        self.texts.on_join(event.player)

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        self.texts.on_quit(event.player)
        self.portals.on_quit(event.player)
