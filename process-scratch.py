with open("scratch.txt", "r", encoding="utf-8") as fh:
    prevdate = ""
    for raw in fh:
        line = raw.strip()
        if not line:
            continue
        if prevdate != line[0:10]:
            print(f"- [{line[0:10]}] {line[11:]}")
        else:
            print(f"  - {line[11:]}")
        prevdate = line[0:10]
