with open("CHANGELOG.md", "w") as file:
    file.write("# Changelog\n\n")
    with open("scratch.txt", "r", encoding="utf-8") as fh:
        prevdate = ""
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if prevdate != line[0:10]:
                restofline = line[11:97] + "..." if len(line[11:]) > 100 else line[11:]
                file.write(f"- [{line[0:10]}] {restofline}\n")
            else:
                restofline = line[11:97] + "..." if len(line[11:]) > 100 else line[11:]
                file.write(f"  - {restofline}\n")
            prevdate = line[0:10]
