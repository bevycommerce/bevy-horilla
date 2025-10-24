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
	docker exec -e PGPASSWORD=mysecretpassword postgres /usr/bin/pg_dump -U postgres --clean horilla > horilla_backup.sql
	zip -r media_backup.zip media/

restore:
	docker cp horilla_backup.sql postgres:/tmp/horilla_backup.sql
	docker exec -e PGPASSWORD=mysecretpassword postgres psql -U postgres -d horilla -f /tmp/horilla_backup.sql
	rm -rf media
	unzip media_backup.zip -d .

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
