.PHONY: up down wipe reset backup restore dblogs applogs dblogsf applogsf adduser shell
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

restore:
	docker cp horilla_backup.sql postgres:/tmp/horilla_backup.sql
	docker exec postgres psql -U postgres -d horilla -f /tmp/horilla_backup.sql
	rm -rf media/*
	unzip media_backup.zip -d .

create_readonly_user1:
	echo "CREATE USER leave_calendar_readonly_user WITH PASSWORD 'readonlypassword'; \
	GRANT CONNECT ON DATABASE horilla TO leave_calendar_readonly_user; \
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
