.PHONY: up down wipe reset backup restore dblogs applogs dblogsf applogsf
up:
	docker compose up --build -d

down:
	docker compose down

wipe:
	docker compose down -v

reset:
	docker system prune -a -f && docker volume prune -f

backup:
	docker exec -e PGPASSWORD=mysecretpassword postgres /usr/bin/pg_dump -U postgres --clean horilla > horilla_backup.sql

restore:
	docker cp horilla_backup.sql postgres:/tmp/horilla_backup.sql
	docker exec -e PGPASSWORD=mysecretpassword postgres psql -U postgres -d horilla -f /tmp/horilla_backup.sql

dblogs:
	docker compose logs postgres

applogs:
	docker compose logs horilla

dblogsf:
	docker compose logs postgres -f

applogsf:
	docker compose logs horilla -f
