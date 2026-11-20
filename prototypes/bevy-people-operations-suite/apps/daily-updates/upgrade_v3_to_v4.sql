-- Apply after v3. No employee, update, work-session or audit data is deleted.
begin;
alter table public.updates add column work_links text not null default '' check(length(work_links)<=6000);
alter table public.updates add column support_person text not null default '' check(length(support_person)<=300);
alter table public.updates add column session_seconds_at_submit numeric;
alter table public.update_versions add column work_links text not null default '';
alter table public.update_versions add column support_person text not null default '';
-- Existing clients remain compatible: default parameters are used for new fields.
drop function public.submit_update(date,text,text,text,text);
create function public.submit_update(p_work_date date,p_kind text,p_progress text,p_next_steps text,p_blockers text,p_work_links text default '',p_support_person text default '')
returns public.updates language plpgsql security definer set search_path='' as $$
declare eid uuid;prev public.updates;result public.updates;w public.work_sessions;
begin
 eid=public.my_employee_id();if p_kind not in ('midday','eod') or p_kind is null then raise exception 'Invalid update type'; end if;
 perform public.check_workday(eid,p_work_date,p_kind);
 perform pg_advisory_xact_lock(hashtextextended(eid::text||p_work_date::text,1));
 select * into w from public.work_sessions where employee_id=eid and work_date=p_work_date;
 if w.id is null then raise exception 'A work sign-in is required. Ask HR to correct a missed sign-in'; end if;
 -- Allow EOD before sign-out for the 30-45 minute handover window.
 -- The eight-hour requirement is still checked separately when closing work.
 if p_kind='eod' and not exists(select 1 from public.updates where employee_id=eid and work_date=p_work_date and kind='midday') and not exists(select 1 from public.midday_exceptions where employee_id=eid and work_date=p_work_date and status in ('pending','accepted')) and not exists(select 1 from public.leaves where employee_id=eid and status='approved' and portion='half' and p_work_date between start_date and end_date) then raise exception 'Submit Mid-day or record a brief reason before EOD'; end if;
 select * into prev from public.updates where employee_id=eid and work_date=p_work_date and kind=p_kind for update;
 if prev.id is not null then
 insert into public.update_versions(update_id,employee_id,version,progress,next_steps,blockers,work_links,support_person) values(prev.id,eid,prev.version,prev.progress,prev.next_steps,prev.blockers,prev.work_links,prev.support_person);
 update public.updates set progress=trim(p_progress),next_steps=trim(p_next_steps),blockers=trim(p_blockers),work_links=trim(coalesce(p_work_links,'')),support_person=trim(coalesce(p_support_person,'')),updated_at=now(),version=version+1,session_seconds_at_submit=public.session_seconds(w) where id=prev.id returning * into result;
 else
 insert into public.updates(employee_id,work_date,kind,progress,next_steps,blockers,work_links,support_person,session_seconds_at_submit) values(eid,p_work_date,p_kind,trim(p_progress),trim(p_next_steps),trim(p_blockers),trim(coalesce(p_work_links,'')),trim(coalesce(p_support_person,'')),public.session_seconds(w)) returning * into result;
 end if;return result;
end $$;
revoke all on function public.submit_update(date,text,text,text,text,text,text) from public;
grant execute on function public.submit_update(date,text,text,text,text,text,text) to authenticated;
create or replace function public.work_action(p_action text,p_note text default '') returns public.work_sessions language plpgsql security definer set search_path='' as $$
declare e public.employees;s public.work_sessions;d date;seconds numeric;before_state jsonb;handover numeric;
begin
 select * into e from public.employees where id=public.my_employee_id();
 if e.id is null then raise exception 'Active employee required'; end if;
 perform pg_advisory_xact_lock(hashtextextended(e.id::text,0));
 select * into s from public.work_sessions where employee_id=e.id and ended_at is null for update;
 if p_action='start' then
  if s.id is not null then return s; end if;
  d=(now() at time zone e.timezone)::date; perform public.check_workday(e.id,d,'eod');
  if exists(select 1 from public.work_sessions where employee_id=e.id and work_date=d) then raise exception 'This workday is already closed. Ask HR for a correction'; end if;
  insert into public.work_sessions(employee_id,work_date) values(e.id,d) returning * into s;
 elsif s.id is null then raise exception 'Sign in to your working day first';
 else
  before_state=to_jsonb(s);seconds=public.session_seconds(s);
  if p_action='pause' then
   if s.paused_at is not null then return s; end if;
   update public.work_sessions set paused_at=now(),updated_at=now() where id=s.id returning * into s;
  elsif p_action='resume' then
   if s.paused_at is null then return s; end if;
   update public.work_sessions set break_seconds=break_seconds+extract(epoch from now()-paused_at),paused_at=null,updated_at=now() where id=s.id returning * into s;
  elsif p_action='short_day' then
   if p_note is null or length(trim(p_note))<10 then raise exception 'A short-day reason is required'; end if;
   update public.work_sessions set close_reason=trim(p_note),needs_review=true,updated_at=now() where id=s.id returning * into s;
  elsif p_action='end' then
   if not exists(select 1 from public.updates where employee_id=e.id and work_date=s.work_date and kind='eod') then raise exception 'Submit your End-of-day update before signing out'; end if;
   select seconds-session_seconds_at_submit into handover from public.updates where employee_id=e.id and work_date=s.work_date and kind='eod';
   if (seconds<28800 or now()-s.started_at>interval '18 hours' or handover<1800) and length(trim(p_note))<10 then raise exception 'A short-day / forgotten-sign-out reason is required'; end if;
   update public.work_sessions set ended_at=now(),break_seconds=break_seconds+case when paused_at is null then 0 else extract(epoch from now()-paused_at) end,paused_at=null,close_reason=trim(p_note),needs_review=(seconds<28800 or now()-started_at>interval '18 hours' or coalesce(handover<1800,false)),updated_at=now() where id=s.id returning * into s;
  else raise exception 'Invalid work action'; end if;
 end if;
 insert into public.session_events(session_id,employee_id,actor_id,action,note,snapshot) values(s.id,e.id,e.id,p_action,left(trim(p_note),2000),jsonb_build_object('before',before_state,'after',to_jsonb(s)));
 return s;
end $$;
revoke all on function public.work_action(text,text) from public;
grant execute on function public.work_action(text,text) to authenticated;

commit;
