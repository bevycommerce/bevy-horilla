.PHONY: up down wipe reset backup restore audit dblogs applogs dblogsf applogsf adduser shell
up:
	docker compose up --build -d

down:
	docker compose down

wipe:
	docker compose down -v

reset:
	docker system prune -a -f && docker volume prune -f

backup:
	docker exec postgres /usr/bin/pg_dump -U postgres --clean horilla > horilla_backup.sql
	zip -r media_backup.zip media/

# Safely restores horilla_backup.sql + media_backup.zip onto THIS host.
# Drops and recreates the database first - restoring pg_dump --clean onto an
# existing populated database silently corrupts it (DROP TABLE without
# CASCADE fails against existing FK-linked data, and the restore continues
# past the failure). See scripts/restore_from_production.sh for details.
# Prompts for confirmation; set CONFIRM_RESTORE=yes to skip the prompt.
restore:
	./scripts/restore_from_production.sh

# Verifies the committed migrations provision a fresh database cleanly and,
# if horilla_backup.sql is present, that restoring it and migrating on top
# also matches models.py. Run after `make restore` and before pointing DNS
# at this host.
audit:
	./scripts/audit_migrations.sh horilla_backup.sql

create_readonly_user1:
	docker exec -i postgres psql -U postgres -d horilla -tAc \
		"SELECT 1 FROM pg_roles WHERE rolname = 'leave_calendar_readonly_user'" \
		| grep -q 1 || echo "CREATE USER leave_calendar_readonly_user WITH PASSWORD 'readonlypassword';" \
		| docker exec -i postgres psql -U postgres -d horilla
	echo "GRANT CONNECT ON DATABASE horilla TO leave_calendar_readonly_user; \
	GRANT USAGE ON SCHEMA public TO leave_calendar_readonly_user; \
	GRANT SELECT ON TABLE public.employee_employee TO leave_calendar_readonly_user; \
	GRANT SELECT ON TABLE public.leave_leaverequest TO leave_calendar_readonly_user;" | docker exec -i postgres psql -U postgres -d horilla

change_pg_password:
	echo "ALTER USER postgres WITH PASSWORD 'newpassword';" | docker exec -i postgres psql -U postgres -d horilla

dblogs:
	docker compose logs db

applogs:
	docker compose logs server

dblogsf:
	docker compose logs db -f

applogsf:
	docker compose logs server -f

adduser:
	docker exec -it horilla bash -c "python3 manage.py createhorillauser; exec bash"

shell:
	docker exec -it horilla bash
