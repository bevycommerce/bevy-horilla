-- Only for a project that has ALREADY run the original v1 schema.sql.
-- Existing employees, updates and revisions are retained.
begin;
drop function if exists public.submit_update(text,text,text,text);
alter table public.employees drop column if exists start_time, drop column if exists midday_minutes, drop column if exists eod_minutes, drop column if exists grace_minutes;
alter table public.updates drop column if exists late;
drop policy if exists leaves_insert on public.leaves;
drop policy if exists leaves_edit on public.leaves;
drop policy if exists holidays_insert on public.holidays;
drop policy if exists holidays_delete on public.holidays;
revoke insert,update,delete on public.leaves,public.holidays from authenticated;
create function public.submit_update(p_work_date date,p_kind text,p_progress text,p_next_steps text,p_blockers text)
returns public.updates language plpgsql security definer set search_path='' as $$
declare
 e public.employees; prev public.updates; result public.updates;
begin
 select * into e from public.employees where id=public.my_employee_id();
 if e.id is null then raise exception 'Active employee access is required'; end if;
 if p_kind not in ('midday','eod') or p_kind is null then raise exception 'Invalid update type'; end if;
 if p_work_date is null or p_work_date>(now() at time zone e.timezone)::date then raise exception 'Choose today or a past work date'; end if;
 if p_work_date<e.join_date or (e.end_date is not null and p_work_date>e.end_date) then raise exception 'Outside employment dates'; end if;
 if not (extract(dow from p_work_date)::integer=any(e.workdays)) then raise exception 'No update is required on this working day'; end if;
 if exists(select 1 from public.holidays h where h.work_date=p_work_date and (h.country is null or h.country=e.country)) then raise exception 'This day is a holiday'; end if;
 if exists(select 1 from public.leaves l where l.employee_id=e.id and l.status='approved' and p_work_date between l.start_date and l.end_date and (l.portion='full' or (l.portion='half' and p_kind='midday'))) then raise exception 'This update is exempt due to approved HR portal leave'; end if;
 perform pg_advisory_xact_lock(hashtextextended(e.id::text||p_work_date::text||p_kind,0));
 select * into prev from public.updates where employee_id=e.id and work_date=p_work_date and kind=p_kind for update;
 if prev.id is not null then
 insert into public.update_versions(update_id,employee_id,version,progress,next_steps,blockers)
 values(prev.id,e.id,prev.version,prev.progress,prev.next_steps,prev.blockers);
 update public.updates set progress=trim(p_progress),next_steps=trim(p_next_steps),blockers=trim(p_blockers),updated_at=now(),version=version+1 where id=prev.id returning * into result;
 else
 insert into public.updates(employee_id,work_date,kind,progress,next_steps,blockers)
 values(e.id,p_work_date,p_kind,trim(p_progress),trim(p_next_steps),trim(p_blockers)) returning * into result;
 end if;
 return result;
end $$;
revoke all on function public.submit_update(date,text,text,text,text) from public;
grant execute on function public.submit_update(date,text,text,text,text) to authenticated;
commit;

