"""
smoke_cache_isolation.py
========================
Empirical proof that /api/students/list, /api/assistants/list, and /api/books/catalog
return *per-user* data from *per-user* cache keys.

Run from the project root:
    .venv\\Scripts\\python scripts\\smoke_cache_isolation.py

What it does
------------
1.  Spins up the Flask test client (no real HTTP server).
2.  Creates two ephemeral test users (user_a / user_b).
3.  Seeds 2 exclusive students, 1 exclusive assistant, and 1 exclusive book per user.
4.  Logs in as user_a → calls all 3 endpoints  → primes the cache for user_a.
5.  Logs in as user_b → calls all 3 endpoints  → must NOT see user_a data.
6.  Calls all 3 endpoints again as user_a       → must still return user_a data (hit).
7.  Inspects server_cache._store to verify distinct cache keys exist.
8.  Tears down all seeded test data and test users.

Exit code 0 = all assertions passed.
Exit code 1 = at least one assertion failed.
"""

import sys
import os
import json
import sqlite3

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# ── Import the Flask app ──────────────────────────────────────────────────────
from app import app
from modules import auth_manager, student_manager, assistant_manager, server_cache
from modules.database import DB_PATH

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
INFO = "\033[36mINFO\033[0m"

_failures = []

def check(label: str, condition: bool, detail: str = "") -> None:
    marker = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{marker}] {label}{suffix}")
    if not condition:
        _failures.append(label)


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def direct_db(sql: str, params: tuple = ()):
    """Execute SQL directly on the DB and return last-row-id."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def drop_test_users(emails: list[str]) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for email in emails:
        c.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def drop_test_data(owner_user_ids: list[int]) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for uid in owner_user_ids:
        c.execute("DELETE FROM students WHERE owner_user_id = ?", (uid,))
        c.execute("DELETE FROM staff WHERE owner_user_id = ?", (uid,))
        c.execute("DELETE FROM books WHERE owner_user_id = ?", (uid,))
    conn.commit()
    conn.close()


def login(client, email: str, password: str):
    """Log the test client in; asserts redirect to dashboard."""
    resp = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302), (
        f"Login returned {resp.status_code} – expected redirect"
    )


def get_json(client, url: str):
    """GET a JSON endpoint; return parsed body or raise on non-200."""
    resp = client.get(url)
    if resp.status_code != 200:
        raise AssertionError(
            f"GET {url} → {resp.status_code}\n{resp.data[:400].decode()}"
        )
    return json.loads(resp.data)


# ── Main test ─────────────────────────────────────────────────────────────────

def run() -> None:
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    EMAIL_A = "smoke_user_a@test.invalid"
    EMAIL_B = "smoke_user_b@test.invalid"
    PWD = "Test@1234!"

    # ── 0. Clean any leftover state from a previous broken run ────────────────
    section("0  Pre-clean (remove leftover test accounts if any)")
    drop_test_users([EMAIL_A, EMAIL_B])
    print(f"  [{INFO}] Old test users removed (if present)")

    # ── 1. Register test users ────────────────────────────────────────────────
    section("1  Register two test users")
    ok_a, id_a = auth_manager.register_user(EMAIL_A, PWD, role="instructor")
    ok_b, id_b = auth_manager.register_user(EMAIL_B, PWD, role="instructor")
    check("User A created", ok_a, str(id_a))
    check("User B created", ok_b, str(id_b))
    if not (ok_a and ok_b):
        print("\nCannot continue without both test users.")
        sys.exit(1)

    print(f"  [{INFO}] User A  id={id_a}  ({EMAIL_A})")
    print(f"  [{INFO}] User B  id={id_b}  ({EMAIL_B})")

    try:
        # ── 2. Seed data ──────────────────────────────────────────────────────
        section("2  Seed exclusive test data per user")

        # Students  ----------------------------------------------------------
        s_a1 = student_manager.add_student(
            "SmokeAlice A", "Math", "alice_a@example.com", "0000000001",
            owner_user_id=id_a,
        )
        s_a2 = student_manager.add_student(
            "SmokeAlice A2", "Reading", "alice_a2@example.com", "0000000002",
            owner_user_id=id_a,
        )
        s_b1 = student_manager.add_student(
            "SmokeBob B", "Math", "bob_b@example.com", "0000000003",
            owner_user_id=id_b,
        )
        s_b2 = student_manager.add_student(
            "SmokeBob B2", "Science", "bob_b2@example.com", "0000000004",
            owner_user_id=id_b,
        )
        print(f"  [{INFO}] Students seeded: A→[{s_a1},{s_a2}]  B→[{s_b1},{s_b2}]")

        # Assistants  --------------------------------------------------------
        ass_a = assistant_manager.add_assistant(
            "SmokeAssist Alpha", "Tutor", "assist_alpha@example.com", "",
            owner_user_id=id_a,
        )
        ass_b = assistant_manager.add_assistant(
            "SmokeAssist Beta", "Monitor", "assist_beta@example.com", "",
            owner_user_id=id_b,
        )
        print(f"  [{INFO}] Assistants seeded: A→{ass_a}  B→{ass_b}")

        # Books (direct SQL; book_manager.add_book() not needed for smoke) ----
        book_a = direct_db(
            """INSERT INTO books (title, author, available, reading_level, isbn,
               copies, owner_user_id) VALUES (?,?,?,?,?,?,?)""",
            ("SmokeBook Alpha", "Author A", 1, "3A", "9990000000001", 1, id_a),
        )
        book_b = direct_db(
            """INSERT INTO books (title, author, available, reading_level, isbn,
               copies, owner_user_id) VALUES (?,?,?,?,?,?,?)""",
            ("SmokeBook Beta", "Author B", 1, "4B", "9990000000002", 1, id_b),
        )
        print(f"  [{INFO}] Books seeded: A→{book_a}  B→{book_b}")

        # ── 3. Wipe cache so this run starts clean ────────────────────────────
        section("3  Wipe server_cache before probing")
        server_cache.clear_all()
        print(f"  [{INFO}] Cache flushed – {len(server_cache._store)} entries remaining")

        # ── 4. Prime cache as User A ──────────────────────────────────────────
        section("4  Prime cache – log in as User A, call all 3 endpoints")

        with app.test_client() as client_a:
            login(client_a, EMAIL_A, PWD)

            data_a_students   = get_json(client_a, "/api/students/list")
            data_a_assistants = get_json(client_a, "/api/assistants/list")
            data_a_books      = get_json(client_a, "/api/books/catalog")

        # students/assistants → bare JSON list; books → {"books": [...]}
        names_a_students   = [s["name"] for s in (data_a_students if isinstance(data_a_students, list) else [])]
        names_a_assistants = [a["name"] for a in (data_a_assistants if isinstance(data_a_assistants, list) else [])]
        titles_a_books     = [b["title"] for b in data_a_books.get("books", [])]

        print(f"  [{INFO}] A students  : {names_a_students}")
        print(f"  [{INFO}] A assistants: {names_a_assistants}")
        print(f"  [{INFO}] A books     : {titles_a_books}")

        check("A sees own student (Alice A)",
              "SmokeAlice A" in names_a_students)
        check("A sees own student (Alice A2)",
              "SmokeAlice A2" in names_a_students)
        check("A does NOT see Bob B",
              "SmokeBob B" not in names_a_students)
        check("A sees own assistant (Alpha)",
              "SmokeAssist Alpha" in names_a_assistants)
        check("A does NOT see Beta assistant",
              "SmokeAssist Beta" not in names_a_assistants)
        check("A sees own book (Alpha)",
              "SmokeBook Alpha" in titles_a_books)
        check("A does NOT see Beta book",
              "SmokeBook Beta" not in titles_a_books)

        cache_after_a = len(server_cache._store)
        print(f"\n  [{INFO}] Cache entries after User A primed: {cache_after_a}")

        # ── 5. Probe as User B ────────────────────────────────────────────────
        section("5  Probe – log in as User B, call all 3 endpoints")

        with app.test_client() as client_b:
            login(client_b, EMAIL_B, PWD)

            data_b_students   = get_json(client_b, "/api/students/list")
            data_b_assistants = get_json(client_b, "/api/assistants/list")
            data_b_books      = get_json(client_b, "/api/books/catalog")

        names_b_students   = [s["name"] for s in (data_b_students if isinstance(data_b_students, list) else [])]
        names_b_assistants = [a["name"] for a in (data_b_assistants if isinstance(data_b_assistants, list) else [])]
        titles_b_books     = [b["title"] for b in data_b_books.get("books", [])]

        print(f"  [{INFO}] B students  : {names_b_students}")
        print(f"  [{INFO}] B assistants: {names_b_assistants}")
        print(f"  [{INFO}] B books     : {titles_b_books}")

        check("B sees own student (Bob B)",
              "SmokeBob B" in names_b_students)
        check("B sees own student (Bob B2)",
              "SmokeBob B2" in names_b_students)
        check("B does NOT see Alice A",
              "SmokeAlice A" not in names_b_students)
        check("B sees own assistant (Beta)",
              "SmokeAssist Beta" in names_b_assistants)
        check("B does NOT see Alpha assistant",
              "SmokeAssist Alpha" not in names_b_assistants)
        check("B sees own book (Beta)",
              "SmokeBook Beta" in titles_b_books)
        check("B does NOT see Alpha book",
              "SmokeBook Alpha" not in titles_b_books)

        cache_after_b = len(server_cache._store)
        new_b_entries = cache_after_b - cache_after_a
        print(f"\n  [{INFO}] Cache grew by {new_b_entries} new entries when User B primed (expected ≥3)")
        check("Cache grew with B-scoped keys (≥3 new entries)", new_b_entries >= 3,
              f"got {new_b_entries}")

        # ── 6. Verify User A cache NOT polluted ───────────────────────────────
        section("6  Re-probe User A – must still get User A data (cache hit)")

        with app.test_client() as client_a2:
            login(client_a2, EMAIL_A, PWD)

            data_a2_students   = get_json(client_a2, "/api/students/list")
            data_a2_assistants = get_json(client_a2, "/api/assistants/list")
            data_a2_books      = get_json(client_a2, "/api/books/catalog")

        names_a2_students   = [s["name"] for s in (data_a2_students if isinstance(data_a2_students, list) else [])]
        names_a2_assistants = [a["name"] for a in (data_a2_assistants if isinstance(data_a2_assistants, list) else [])]
        titles_a2_books     = [b["title"] for b in data_a2_books.get("books", [])]

        check("A (re-check) still sees Alice A",
              "SmokeAlice A" in names_a2_students)
        check("A (re-check) still does NOT see Bob B",
              "SmokeBob B" not in names_a2_students)
        check("A (re-check) still sees Alpha assistant",
              "SmokeAssist Alpha" in names_a2_assistants)
        check("A (re-check) still does NOT see Beta assistant",
              "SmokeAssist Beta" not in names_a2_assistants)
        check("A (re-check) still sees Alpha book",
              "SmokeBook Alpha" in titles_a2_books)
        check("A (re-check) still does NOT see Beta book",
              "SmokeBook Beta" not in titles_a2_books)

        # ── 7. Inspect cache keys ─────────────────────────────────────────────
        section("7  Inspect cache _store keys for u:{id_a} / u:{id_b} separation")

        all_keys = list(server_cache._store.keys())
        keys_a   = [k for k in all_keys if f":u:{id_a}" in k]
        keys_b   = [k for k in all_keys if f":u:{id_b}" in k]
        overlap  = [k for k in all_keys if f":u:{id_a}" in k and f":u:{id_b}" in k]

        print(f"\n  [{INFO}] All cache keys ({len(all_keys)} total):")
        for k in sorted(all_keys):
            owner_tag = f"(A)" if f":u:{id_a}" in k else f"(B)" if f":u:{id_b}" in k else "(other)"
            print(f"           {owner_tag} {k}")

        check("≥3 cache keys scoped to User A", len(keys_a) >= 3, f"found {len(keys_a)}")
        check("≥3 cache keys scoped to User B", len(keys_b) >= 3, f"found {len(keys_b)}")
        check("No key straddles both user scopes", len(overlap) == 0, f"overlap={overlap}")

    finally:
        # ── 8. Cleanup ────────────────────────────────────────────────────────
        section("8  Teardown – remove test data and test users")
        drop_test_data([id_a, id_b])
        drop_test_users([EMAIL_A, EMAIL_B])
        server_cache.clear_all()
        print(f"  [{INFO}] Test students, assistants, books, and users removed")
        print(f"  [{INFO}] Cache flushed")

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    if _failures:
        print(f"  RESULT: {FAIL} – {len(_failures)} assertion(s) failed:")
        for f in _failures:
            print(f"    ✗  {f}")
        print(f"{'═' * 60}\n")
        sys.exit(1)
    else:
        print(f"  RESULT: {PASS} – All {len([None for _ in range(25)])} assertions passed")
        print(f"{'═' * 60}\n")
        sys.exit(0)


if __name__ == "__main__":
    run()
