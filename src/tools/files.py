import os
import subprocess
from pathlib import Path

SEARCH_ROOTS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
]


def find_files(query, max_results=10):
    query = query.lower().strip()
    results = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in {"node_modules", "__pycache__"}
            ]

            for filename in filenames:
                if query in filename.lower():
                    full_path = Path(dirpath) / filename
                    results.append(str(full_path))

                    if len(results) >= max_results:
                        return results

    return results


def reveal_file(path):
    path = str(path)

    if not os.path.exists(path):
        return f"File does not exist: {path}"

    subprocess.run(["open", "-R", path])
    return f"Revealed file in Finder: {path}"


def open_file(path):
    path = str(path)

    if not os.path.exists(path):
        return f"File does not exist: {path}"

    subprocess.run(["open", path])
    return f"Opened file: {path}"


def find_and_reveal_file(query):
    results = find_files(query)

    if not results:
        return f"No files found matching: {query}"

    best_match = results[0]
    reveal_file(best_match)

    if len(results) == 1:
        return f"Found and revealed: {best_match}"

    other_matches = "\n".join(results[1:5])
    return f"Revealed best match: {best_match}\n\nOther matches:\n{other_matches}"


def delete_file_by_query(query):
    results = find_files(query, max_results=5)

    if not results:
        return f"No files found matching: {query}"

    target = results[0]

    print("\nLUMA: I found this file:")
    print(target)

    if len(results) > 1:
        print("\nOther possible matches:")
        for item in results[1:]:
            print(f"- {item}")

    confirm = input("\nDelete the first file? yes/no: ").strip().lower()

    if confirm not in {"yes", "y"}:
        return "Deletion cancelled."

    try:
        os.remove(target)
        return f"Deleted: {target}"
    except Exception as e:
        return f"Failed to delete file: {e}"
