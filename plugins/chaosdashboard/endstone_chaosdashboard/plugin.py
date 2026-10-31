import json
import queue
import secrets

from endstone.plugin import Plugin

from endstone_chaosdashboard.web import DashboardServer

DEFAULT_PORT = 8099
QUEUE_TICKS = 5
SNAPSHOT_TICKS = 20


class ChaosDashboardPlugin(Plugin):
    prefix = "ChaosDashboard"
    api_version = "0.11"

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        settings = self._settings()
        self.jobs: queue.Queue = queue.Queue()
        self.snapshot: dict = {}
        self._take_snapshot()
        self.web = DashboardServer(self, settings["host"], settings["port"], settings["token"])
        self.web.start()
        self.logger.info(f"Dashboard on port {settings['port']}")
        self.server.scheduler.run_task(self, self._run_jobs, delay=QUEUE_TICKS, period=QUEUE_TICKS)
        self.server.scheduler.run_task(self, self._take_snapshot, delay=SNAPSHOT_TICKS, period=SNAPSHOT_TICKS)

    def on_disable(self) -> None:
        self.web.stop()

    def _settings(self) -> dict:
        path = self.data_folder / "settings.json"
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        settings.setdefault("host", "0.0.0.0")
        settings.setdefault("port", DEFAULT_PORT)
        settings.setdefault("token", secrets.token_urlsafe(18))
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return settings

    def _manager(self, name: str):
        plugin = self.server.plugin_manager.get_plugin(name)
        return getattr(plugin, "manager", None) if plugin is not None else None

    def _take_snapshot(self) -> None:
        texts, portals, ranks = (self._manager(n) for n in ("chaostexts", "chaosportals", "chaosranks"))
        self.snapshot = {
            "name": self.server.name,
            "version": self.server.minecraft_version,
            "players": [
                {"name": p.name, "rank": ranks.group_of(p.name) if ranks else None, "dimension": p.dimension.name}
                for p in self.server.online_players
            ],
            "texts": texts.texts if texts else None,
            "portals": portals.portals if portals else None,
            "ranks": ranks.groups if ranks else None,
            "assigned": ranks.players if ranks else None,
            "default_rank": ranks.data["default"] if ranks else None,
        }

    def _run_jobs(self) -> None:
        while True:
            try:
                action, done = self.jobs.get_nowait()
            except queue.Empty:
                return
            try:
                done["result"] = self._perform(action)
            except Exception as error:  # the web thread reports this to the browser
                done["error"] = str(error)
            done["event"].set()

    def _perform(self, action: dict) -> str:
        kind = action["type"]
        if kind == "command":
            self.server.dispatch_command(self.server.command_sender, action["line"])
            return "Befehl ausgeführt."
        if kind == "kick":
            player = self.server.get_player(action["player"])
            if player is None:
                raise ValueError("Spieler ist nicht online.")
            player.kick(action.get("reason") or "Vom Dashboard gekickt.")
            return f"{action['player']} gekickt."
        if kind == "rank":
            ranks = self._manager("chaosranks")
            if action["rank"] not in ranks.groups:
                raise ValueError("Unbekannter Rang.")
            ranks.assign(action["player"], action["rank"])
            return f"{action['player']} ist jetzt {action['rank']}."
        if kind == "text_remove":
            self._manager("chaostexts").remove(action["id"])
            return "Text entfernt."
        if kind == "portal_remove":
            portals = self._manager("chaosportals")
            del portals.portals[action["name"]]
            portals.store.save()
            return "Portal entfernt."
        raise ValueError("Unbekannte Aktion.")
