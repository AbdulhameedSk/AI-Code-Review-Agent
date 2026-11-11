"""
evals/fixtures.py — diffs with KNOWN planted bugs.

Evals need ground truth: a diff where we already know what a good reviewer
should catch. Each fixture has the diff and the keywords a correct finding
should mention. Simple but honest scoring.
"""

SQL_INJECTION_DIFF = """diff --git a/app/db.py b/app/db.py
new file mode 100644
--- /dev/null
+++ b/app/db.py
@@ -0,0 +1,8 @@
+import sqlite3
+
+def get_user(username):
+    conn = sqlite3.connect("app.db")
+    query = f"SELECT * FROM users WHERE name = '{username}'"
+    return conn.execute(query).fetchone()
+
+def close(conn):
+    conn.close()
"""

HARDCODED_SECRET_DIFF = """diff --git a/config.py b/config.py
new file mode 100644
--- /dev/null
+++ b/config.py
@@ -0,0 +1,4 @@
+API_KEY = "sk-live-9f8e7d6c5b4a"
+DB_PASSWORD = "hunter2"
+
+TIMEOUT = 30
"""

CLEAN_DIFF = """diff --git a/utils.py b/utils.py
new file mode 100644
--- /dev/null
+++ b/utils.py
@@ -0,0 +1,6 @@
+def clamp(value, low, high):
+    return max(low, min(high, value))
+
+def chunk_list(items, size):
+    return [items[i:i+size] for i in range(0, len(items), size)]
"""

FIXTURES = [
    {"name": "sql_injection", "diff": SQL_INJECTION_DIFF,
     "expect": {"keywords": ["sql", "injection", "f-string", "parameter"],
                "min_findings": 1}},
    {"name": "hardcoded_secret", "diff": HARDCODED_SECRET_DIFF,
     "expect": {"keywords": ["secret", "key", "password", "hardcod"],
                "min_findings": 1}},
    {"name": "clean_code", "diff": CLEAN_DIFF,
     "expect": {"keywords": [], "max_findings": 0}},
]
