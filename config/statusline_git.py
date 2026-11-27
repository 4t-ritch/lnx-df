"""Git branch labels using the Fish prompt's porcelain and symbol order."""

STATUS_ARGS = (
    "--no-optional-locks", "status", "--porcelain=2", "--branch", "--no-renames",
)


def branch_label(status):
    branch = oid = ""
    ahead = behind = dirty = False
    for line in (status or "").split("\n"):
        if line.startswith("# branch.head "):
            branch = line.removeprefix("# branch.head ")
        elif line.startswith("# branch.oid "):
            oid = line.removeprefix("# branch.oid ")
        elif line.startswith("# branch.ab "):
            counts = line.split()[2:]
            if len(counts) == 2:
                ahead, behind = counts[0] != "+0", counts[1] != "-0"
        elif line.startswith(("1 ", "2 ", "u ", "? ")):
            dirty = True
    if not branch or branch == "(detached)":
        branch = oid[:7]
    if not branch:
        return None
    symbols = (">" if ahead else "") + ("<" if behind else "") + ("!" if dirty else "")
    return f"{branch} {symbols}" if symbols else branch
