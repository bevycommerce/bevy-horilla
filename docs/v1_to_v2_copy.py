#!/usr/bin/env python3
"""Copy a Horilla v1 Postgres database into an already-migrated v2 database.

The source connection is read-only. Primary keys are preserved. Permission and
group ids are not copied, because v2 migrate assigns its own. Memberships are
reattached by group name and by (app_label, codename).

Run only against a v2 database that has been migrated and does not yet contain
employees. The v1 volume is never written.
"""

from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2.extras import Json, execute_values

# Tables v2 recreate itself, or that diverge and are kept only in the v1 archive.
SKIP_EXACT = {
    "django_migrations",
    "django_session",
    "django_admin_log",
    "django_content_type",
    "django_site",
    "django_cache",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
}
SKIP_PREFIXES = ("django_", "auditlog_", "workspace_", "daily_updates_")

# Model defaults for columns v1 does not have. Used only when v2 left no
# database default, so INSERT would otherwise write NULL into NOT NULL.
KNOWN_FILLS = {
    "cancellation_requested": False,
    "daily_leave_amount_base": "wage",
    "loss_of_pay_is_pretax": True,
    "daily_leave_amount_divisor": "calendar_days",
}

USER_SOURCE = "auth_user"
USER_DEST = "horilla_auth_horillauser"


def log(message: str) -> None:
    print(message, flush=True)


def ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise SystemExit(f"Unsafe SQL identifier: {name!r}")
    return name


def q(name: str) -> str:
    return '"' + ident(name) + '"'


def skip_table(name: str) -> str | None:
    if name in SKIP_EXACT or name == USER_SOURCE:
        return "handled separately" if name == USER_SOURCE else "rebuilt by migrate"
    if "historical" in name:
        return "history stays in the v1 database"
    if name.startswith(SKIP_PREFIXES):
        return "rebuilt by migrate or left empty"
    return None


def columns(cursor, table: str) -> list[tuple]:
    cursor.execute(
        """
        SELECT column_name, is_nullable, column_default, data_type,
               is_identity, identity_generation
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return cursor.fetchall()


def table_names(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def primary_key(cursor, table: str) -> list[str]:
    cursor.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
        ORDER BY array_position(i.indkey, a.attnum)
        """,
        (table,),
    )
    return [row[0] for row in cursor.fetchall()]


def user_fk_renames(src, dst) -> dict[tuple[str, str], str]:
    """Map (v1 table, v1 column) -> v2 column when the user table rename moved it."""
    src.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema = tc.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND ccu.table_name = %s
        """,
        (USER_SOURCE,),
    )
    src_fks = {(table, column) for table, column in src.fetchall()}
    dst.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema = tc.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND ccu.table_name = %s
        """,
        (USER_DEST,),
    )
    dst_by_table: dict[str, set[str]] = {}
    for table, column in dst.fetchall():
        dst_by_table.setdefault(table, set()).add(column)
    renames = {}
    for table, column in src_fks:
        dest_cols = dst_by_table.get(table, set())
        if column in dest_cols or not dest_cols:
            continue
        if column == "user_id" and "horillauser_id" in dest_cols:
            renames[(table, column)] = "horillauser_id"
    return renames


def count(cursor, table: str) -> int:
    cursor.execute(f"SELECT count(*) FROM {q(table)}")
    return int(cursor.fetchone()[0])


def copy_table(src, dst, source: str, dest: str, renames: dict[str, str]) -> dict:
    src_cols = {row[0]: row for row in columns(src, source)}
    dst_cols = {row[0]: row for row in columns(dst, dest)}
    if not src_cols:
        return {"table": dest, "status": "missing-source", "rows": 0}
    if not dst_cols:
        return {"table": dest, "status": "missing-dest", "rows": 0}

    src_select = []
    dest_names = []
    skipped_types = []
    for source_col in src_cols:
        dest_col = renames.get(source_col, source_col)
        if dest_col not in dst_cols:
            continue
        src_type = src_cols[source_col][3]
        dst_type = dst_cols[dest_col][3]
        # v2 widens some ids from integer to bigint. Postgres accepts that
        # assignment. Array-to-jsonb does not, so those columns are left out.
        widened = {("integer", "bigint"), ("smallint", "bigint"), ("smallint", "integer")}
        if src_type != dst_type and (src_type, dst_type) not in widened:
            skipped_types.append(f"{dest_col}:{src_type}->{dst_type}")
            continue
        src_select.append(source_col)
        dest_names.append(dest_col)

    src.execute(f"SELECT {', '.join(q(c) for c in src_select)} FROM {q(source)}")
    rows = src.fetchall()
    result = {
        "table": f"{source}->{dest}",
        "status": "ok",
        "rows": len(rows),
        "fills": [],
        "skipped_types": skipped_types,
    }
    if not rows:
        return result

    fills = []
    for name, (_n, nullable, default, data_type, _ident, _gen) in dst_cols.items():
        if name in dest_names or nullable == "YES" or default is not None:
            continue
        if name in KNOWN_FILLS:
            fills.append((name, KNOWN_FILLS[name]))
            continue
        if data_type in {"character varying", "character", "text"}:
            fills.append((name, ""))
            continue
        if data_type == "boolean":
            fills.append((name, False))
            continue
        skipped_names = {item.split(":", 1)[0] for item in skipped_types}
        if name in skipped_names:
            result["status"] = "skipped-type-mismatch"
            result["rows"] = 0
            return result
        raise SystemExit(
            f"{dest}.{name} is NOT NULL, has no default, and is not on the v1 table"
        )

    dest_names.extend(name for name, _value in fills)
    fill_values = tuple(value for _name, value in fills)
    if fill_values:
        rows = [tuple(row) + fill_values for row in rows]
    result["fills"] = [name for name, _value in fills]
    # psycopg2 sends a Python list as a Postgres array. A jsonb column that
    # stored a list has to go back as json, or the insert is rejected.
    json_at = [
        index
        for index, name in enumerate(dest_names)
        if dst_cols[name][3] in {"json", "jsonb"}
    ]
    if json_at:
        adapted = []
        for row in rows:
            row = list(row)
            for index in json_at:
                if row[index] is not None and not isinstance(row[index], Json):
                    row[index] = Json(row[index])
            adapted.append(tuple(row))
        rows = adapted

    identity = any(dst_cols[name][4] == "YES" for name in dest_names)
    override = " OVERRIDING SYSTEM VALUE" if identity else ""
    pk = [col for col in primary_key(dst, dest) if col in dest_names]
    sql = (
        f"INSERT INTO {q(dest)} ({', '.join(q(c) for c in dest_names)}) "
        f"{override} VALUES %s"
    )
    if pk:
        updates = [f"{q(c)} = EXCLUDED.{q(c)}" for c in dest_names if c not in pk]
        conflict = ", ".join(q(c) for c in pk)
        if updates:
            sql += f" ON CONFLICT ({conflict}) DO UPDATE SET " + ", ".join(updates)
        else:
            sql += f" ON CONFLICT ({conflict}) DO NOTHING"
    execute_values(dst, sql, rows, page_size=500)
    return result


def reset_sequences(dst, tables: list[str]) -> None:
    for table in tables:
        if "id" not in {row[0] for row in columns(dst, table)}:
            continue
        dst.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
        row = dst.fetchone()
        seq = row[0] if row else None
        if not seq:
            continue
        dst.execute(
            f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {q(table)}), 1), true)",
            (seq,),
        )


def assign_null_stages(dst) -> int:
    dst.execute(
        """
        SELECT id, recruitment_id_id, hired, canceled
        FROM recruitment_candidate
        WHERE stage_id_id IS NULL
        ORDER BY id
        """
    )
    pending = dst.fetchall()
    assigned = 0
    for candidate_id, recruitment_id, hired, canceled in pending:
        if recruitment_id is None:
            raise SystemExit(f"Candidate {candidate_id} has no recruitment and no stage")
        wanted = "hired" if hired else "cancelled" if canceled else None
        dst.execute(
            """
            SELECT id FROM recruitment_stage
            WHERE recruitment_id_id = %s
              AND (%s::varchar IS NULL OR stage_type = %s)
            ORDER BY sequence NULLS LAST, id
            LIMIT 1
            """,
            (recruitment_id, wanted, wanted),
        )
        stage = dst.fetchone()
        if stage is None and wanted:
            dst.execute(
                """
                SELECT id FROM recruitment_stage
                WHERE recruitment_id_id = %s
                ORDER BY sequence NULLS LAST, id
                LIMIT 1
                """,
                (recruitment_id,),
            )
            stage = dst.fetchone()
        if stage is None:
            raise SystemExit(
                f"Candidate {candidate_id} has no stage to assign in recruitment {recruitment_id}"
            )
        dst.execute(
            "UPDATE recruitment_candidate SET stage_id_id = %s WHERE id = %s",
            (stage[0], candidate_id),
        )
        assigned += 1
    return assigned


def remap_access(src, dst) -> None:
    src.execute("SELECT id, name FROM auth_group ORDER BY id")
    groups = src.fetchall()
    src.execute(
        """
        SELECT ug.user_id, g.name
        FROM auth_user_groups ug
        JOIN auth_group g ON g.id = ug.group_id
        """
    )
    memberships = src.fetchall()
    src.execute(
        """
        SELECT g.name, ct.app_label, p.codename
        FROM auth_group_permissions gp
        JOIN auth_group g ON g.id = gp.group_id
        JOIN auth_permission p ON p.id = gp.permission_id
        JOIN django_content_type ct ON ct.id = p.content_type_id
        """
    )
    group_perms = src.fetchall()
    src.execute(
        """
        SELECT up.user_id, ct.app_label, p.codename
        FROM auth_user_user_permissions up
        JOIN auth_permission p ON p.id = up.permission_id
        JOIN django_content_type ct ON ct.id = p.content_type_id
        """
    )
    user_perms = src.fetchall()

    dst.execute(
        """
        SELECT p.id, ct.app_label, p.codename
        FROM auth_permission p
        JOIN django_content_type ct ON ct.id = p.content_type_id
        """
    )
    perm_ids = {(app, code): pid for pid, app, code in dst.fetchall()}

    group_ids = {}
    for _gid, name in groups:
        dst.execute("SELECT id FROM auth_group WHERE name = %s", (name,))
        row = dst.fetchone()
        if row:
            group_ids[name] = row[0]
            continue
        dst.execute(
            "INSERT INTO auth_group (name) VALUES (%s) RETURNING id",
            (name,),
        )
        group_ids[name] = dst.fetchone()[0]

    for name, app, code in group_perms:
        pid = perm_ids.get((app, code))
        gid = group_ids.get(name)
        if pid and gid:
            dst.execute(
                """
                INSERT INTO auth_group_permissions (group_id, permission_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (gid, pid),
            )

    member_rows = []
    for user_id, name in memberships:
        gid = group_ids.get(name)
        if gid:
            member_rows.append((user_id, gid))
    if "Talent Acquisition Viewer" in group_ids and "Recruiter" in {
        name for _gid, name in []
    }:
        pass
    dst.execute("SELECT id FROM auth_group WHERE name = 'Recruiter'")
    recruiter = dst.fetchone()
    if recruiter:
        for user_id, name in memberships:
            if name == "Talent Acquisition Viewer":
                member_rows.append((user_id, recruiter[0]))
    if member_rows:
        execute_values(
            dst,
            """
            INSERT INTO horilla_auth_horillauser_groups (horillauser_id, group_id)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            member_rows,
        )

    perm_rows = []
    missing = 0
    for user_id, app, code in user_perms:
        pid = perm_ids.get((app, code))
        if pid:
            perm_rows.append((user_id, pid))
        else:
            missing += 1
    if perm_rows:
        execute_values(
            dst,
            """
            INSERT INTO horilla_auth_horillauser_user_permissions
                (horillauser_id, permission_id)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            perm_rows,
        )
    log(
        f"access groups={len(group_ids)} memberships={len(member_rows)} "
        f"user_perms={len(perm_rows)} missing_perms={missing}"
    )


def validate(dst) -> None:
    checks = [
        (
            "employee_user",
            """
            SELECT count(*) FROM employee_employee e
            LEFT JOIN horilla_auth_horillauser u ON u.id = e.employee_user_id_id
            WHERE e.employee_user_id_id IS NOT NULL AND u.id IS NULL
            """,
        ),
        (
            "work_info_employee",
            """
            SELECT count(*) FROM employee_employeeworkinformation w
            LEFT JOIN employee_employee e ON e.id = w.employee_id_id
            WHERE e.id IS NULL
            """,
        ),
        (
            "attendance_employee",
            """
            SELECT count(*) FROM attendance_attendance a
            LEFT JOIN employee_employee e ON e.id = a.employee_id_id
            WHERE e.id IS NULL
            """,
        ),
        (
            "leave_employee",
            """
            SELECT count(*) FROM leave_leaverequest l
            LEFT JOIN employee_employee e ON e.id = l.employee_id_id
            WHERE e.id IS NULL
            """,
        ),
        (
            "contract_employee",
            """
            SELECT count(*) FROM payroll_contract c
            LEFT JOIN employee_employee e ON e.id = c.employee_id_id
            WHERE e.id IS NULL
            """,
        ),
        (
            "candidate_stage",
            """
            SELECT count(*) FROM recruitment_candidate c
            LEFT JOIN recruitment_stage s ON s.id = c.stage_id_id
            WHERE c.stage_id_id IS NOT NULL AND s.id IS NULL
            """,
        ),
        (
            "null_stage",
            "SELECT count(*) FROM recruitment_candidate WHERE stage_id_id IS NULL",
        ),
    ]
    failed = False
    for label, sql in checks:
        dst.execute(sql)
        found = int(dst.fetchone()[0])
        log(f"check {label}={found}")
        if found:
            failed = True
    if failed:
        raise SystemExit("Validation failed")


def main() -> None:
    source_dsn = os.environ["V1_SOURCE_DATABASE_URL"]
    dest_dsn = os.environ["DATABASE_URL"]
    src = psycopg2.connect(source_dsn)
    src.set_session(readonly=True, autocommit=True)
    dst = psycopg2.connect(dest_dsn)
    dst.autocommit = False
    try:
        with src.cursor() as sc, dst.cursor() as dc:
            dc.execute("SELECT count(*) FROM employee_employee")
            if int(dc.fetchone()[0]) != 0:
                raise SystemExit("Destination already has employees. Refusing.")
            dc.execute("SELECT to_regclass('public.horilla_auth_horillauser')")
            if dc.fetchone()[0] is None:
                raise SystemExit("Destination has no horilla_auth_horillauser. Migrate v2 first.")

            renames = user_fk_renames(sc, dc)
            log(f"user column renames={len(renames)}")
            src_tables = table_names(sc)
            dst_tables = set(table_names(dc))

            dc.execute("SET session_replication_role = replica")
            # v1 allows more than one cancelled/hired stage on a recruitment.
            # v2 migrate adds a unique constraint that rejects those rows.
            # The stage ids have to stay, because candidates point at them.
            dc.execute(
                "DROP INDEX IF EXISTS unique_special_stage_type_per_recruitment"
            )
            plan = [(USER_SOURCE, USER_DEST, {})]
            for name in src_tables:
                reason = skip_table(name)
                if reason:
                    continue
                if name not in dst_tables:
                    log(f"skip {name}: not on v2")
                    continue
                table_renames = {
                    column: dest_col
                    for (table, column), dest_col in renames.items()
                    if table == name
                }
                plan.append((name, name, table_renames))

            for _source, dest, _rename in plan:
                if dest in dst_tables or dest == USER_DEST:
                    dc.execute(f"TRUNCATE TABLE {q(dest)} CASCADE")

            copied = []
            for source, dest, table_renames in plan:
                result = copy_table(sc, dc, source, dest, table_renames)
                copied.append(result)
                log(
                    f"copied {result['table']} rows={result['rows']} "
                    f"fills={','.join(result.get('fills') or [])} "
                    f"skipped_types={','.join(result.get('skipped_types') or [])}"
                )
            reset_sequences(dc, [dest for _s, dest, _r in plan])
            stages = assign_null_stages(dc)
            log(f"assigned_null_stages={stages}")
            dc.execute("SET session_replication_role = DEFAULT")
            remap_access(sc, dc)
            validate(dc)
            for label, table in (
                ("users", USER_DEST),
                ("employees", "employee_employee"),
                ("attendance", "attendance_attendance"),
                ("leave", "leave_leaverequest"),
                ("contracts", "payroll_contract"),
                ("candidates", "recruitment_candidate"),
            ):
                log(f"count {label}={count(dc, table)}")
        dst.commit()
        log("committed")
    except Exception:
        dst.rollback()
        raise
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        log(str(exc))
        sys.exit(1)
