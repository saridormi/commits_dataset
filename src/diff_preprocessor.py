import re
from typing import Dict, List


class DiffPreprocessor:
    """
    This class parses raw diff string into a list of files modifications.

    Each modification is a dictionary with following keys:

    * `change_type` (str): one of "ADD", "DELETE", "RENAME", "MODIFY"
    * `old_path` (str): path to modified file before commit
    * `new_path` (str): path to modified file after commit
    * `diff` (str): file diff without unchanged lines and special lines from git
    """

    @staticmethod
    def _preprocess_single_file_diff(header: str, diff: str) -> Dict[str, str]:
        diff_lines = diff.split("\n")
        mod = {}

        if diff_lines[0].strip().startswith("new file"):
            mod["change_type"] = "ADD"
            mod["old_path"] = ""
            mod["new_path"] = header.split()[1].strip("b/")

        elif diff_lines[0].strip().startswith("deleted file"):
            mod["change_type"] = "DELETE"
            mod["old_path"] = header.split()[0].strip("a/")
            mod["new_path"] = ""

        elif diff_lines[0].strip().startswith("similarity index"):
            mod["change_type"] = "RENAME"
            mod["old_path"] = header.split()[0].strip("a/")
            mod["new_path"] = header.split()[1].strip("b/")

        else:
            mod["change_type"] = "MODIFY"
            mod["old_path"] = header.split()[0].strip("a/")
            mod["new_path"] = header.split()[1].strip("b/")

        processed_diff = []
        for line in diff_lines:
            line = line.strip()
            if line.startswith("+") and not (line.startswith("+++ b/") or line.startswith("+++ /dev/null")):
                processed_diff.append(line)
            elif line.startswith("-") and not (line.startswith("--- a/") or line.startswith("--- /dev/null")):
                processed_diff.append(line)
            elif line.startswith("Binary files") and line.endswith("differ"):
                processed_diff.append(line)

        mod["diff"] = "\n".join(processed_diff)
        return mod

    @staticmethod
    def preprocess(diff: str) -> List[Dict[str, str]]:
        files_diffs = re.split("diff --git(.*?)\n", diff)[1:]

        result = []
        i = 0
        while i + 1 < len(files_diffs):
            result.append(DiffPreprocessor._preprocess_single_file_diff(files_diffs[i], files_diffs[i + 1]))
            i += 2

        return result
