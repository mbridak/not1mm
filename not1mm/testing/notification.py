"""
Simple D-Bus desktop notification helper.

Uses the org.freedesktop.Notifications D-Bus API via python-dbus.
"""

from typing import Dict, Iterable, Optional

try:
    import dbus
except Exception as _err:  # pragma: no cover - runtime import check
    dbus = None


class DbusNotification:
    """Send desktop notifications over the session D-Bus.

    Example:
        notifier = DbusNotification("MyApp")
        nid = notifier.notify("Hello", "This is a body", timeout=3000)

    Methods:
        notify(summary, body, icon, timeout, actions, hints, replaces_id) -> int
        close(nid)
    """

    def __init__(self, app_name: str = "Not1MM") -> None:
        if dbus is None:
            raise RuntimeError(
                "dbus-python is required (install system package or 'pip install dbus-python')."
            )
        self.app_name = app_name
        self.bus = dbus.SessionBus()
        obj = self.bus.get_object(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
        )
        self.iface = dbus.Interface(obj, "org.freedesktop.Notifications")

    def notify(
        self,
        summary: str,
        body: str = "",
        icon: str = "",
        timeout: int = 5000,
        actions: Optional[Iterable[str]] = None,
        hints: Optional[Dict[str, object]] = None,
        replaces_id: int = 0,
    ) -> int:
        """Send a notification.

        Args:
            summary: short summary/title
            body: longer body text
            icon: icon name or path (string)
            timeout: milliseconds before the notification expires (int)
            actions: list of action identifiers and labels (flat list of strings)
            hints: dict of hint keys to values (e.g., {'urgency': dbus.Byte(1)})
            replaces_id: notification id to replace

        Returns:
            notification id (int)
        """
        actions = actions or []
        hints = hints or {}

        actions_arr = dbus.Array(actions, signature="s")
        hints_dict = dbus.Dictionary(hints, signature="sv")

        nid = self.iface.Notify(
            self.app_name,
            int(replaces_id),
            icon,
            summary,
            body,
            actions_arr,
            hints_dict,
            int(timeout),
        )
        try:
            return int(nid)
        except Exception:
            return nid

    def close(self, nid: int) -> None:
        """Close a previously shown notification by id."""
        try:
            self.iface.CloseNotification(int(nid))
        except Exception:
            # ignore failures to close (e.g., invalid id)
            pass


if __name__ == "__main__":
    # Simple demo usage
    try:
        n = DbusNotification("Not1MM")
        nid = n.notify("Test notification", "This was sent over D-Bus", timeout=5000)
        print("Notification sent, id:", nid)
    except RuntimeError as e:
        print("Runtime error:", e)
        print(
            "On many systems you must install the system package 'python3-dbus' or similar."
        )
