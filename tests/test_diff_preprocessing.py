from src.diff_preprocessor import DiffPreprocessor


modify_diff = """diff --git a/old_path b/old_path
index b95f012..fd0e99a 100644
--- a/old_fname
+++ b/old_fname
@@ -3,4 +3,5 @@ 
context line 1
context line 2
context line 3
-line 1
+line 1
context line 1
context line 2
context line 3
"""

add_diff = """diff --git a/new_path b/new_path
new file mode 100644
index 0000000..d9ec240
--- /dev/null
+++ b/new_fname
@@ -0,0 +1,3 @@
+line 1
+line 2
"""

delete_diff = """diff --git a/old_path b/old_path
deleted file mode 100644
index 553f0ec..0000000
--- a/old_fname
+++ /dev/null
@@ -1,3 +0,0 @@
-line 1
-line 2 
\\ No newline at end of file
"""

rename_diff = """diff --git a/old_path b/new_path
similarity index 100%
rename from old_fname
rename to new_fname
"""


def test_modify_file():
    assert DiffPreprocessor.preprocess(modify_diff) == [
        {"old_path": "old_path", "new_path": "old_path", "change_type": "MODIFY", "diff": "-line 1\n+line 1"}
    ]


def test_add_file():
    assert DiffPreprocessor.preprocess(add_diff) == [
        {"old_path": "", "new_path": "new_path", "change_type": "ADD", "diff": "+line 1\n+line 2"}
    ]


def test_delete_file():
    assert DiffPreprocessor.preprocess(delete_diff) == [
        {"old_path": "old_path", "new_path": "", "change_type": "DELETE", "diff": "-line 1\n-line 2"}
    ]


def test_rename_file():
    assert DiffPreprocessor.preprocess(rename_diff) == [
        {"old_path": "old_path", "new_path": "new_path", "change_type": "RENAME", "diff": ""}
    ]
