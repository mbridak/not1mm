import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("parse_udc")


class UDC:
    """Parse UDC files"""

    # Sections
    # [Author]
    # [File]
    # [Contest]

    def __init__(self) -> None: ...

    def parse_udc(self, path: str) -> dict[str, dict[str, str]]:
        """Parse a .udc file at `path` and return a dict of sections.

        Each section is a dict of key -> value (both stripped). Lines without
        an '=' are ignored. Empty values are preserved as empty strings.
        """
        result: dict[str, dict[str, str]] = {}
        current_section: str | None = None

        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    if current_section not in result:
                        result[current_section] = {}
                    continue
                if current_section is None:
                    # skip any lines before first section
                    continue

                # split on first '='; keys or values may contain '=' rarely
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                result[current_section][key] = value

        return result
