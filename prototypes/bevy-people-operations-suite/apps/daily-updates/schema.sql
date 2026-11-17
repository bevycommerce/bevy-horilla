-- Bevy Daily Updates. Run once in a NEW Supabase project SQL Editor.
begin;
create table public.employees (
 id uuid primary key default gen_random_uuid(),
 email text not null unique check(email=lower(trim(email))),
 full_name text not null check(length(trim(full_name)) between 2 and 120),
 department text not null default 'General', country text not null default 'Bangladesh',
 role text not null default 'employee' check(role in ('employee','hr')),
 active boolean not null default true,
 join_date date not null default current_date, end_date date,
 timezone text not null default 'Asia/Dhaka' check(timezone in ('Asia/Dhaka','Asia/Karachi','America/Toronto','UTC')),
 workdays integer[] not null default '{1,2,3,4,5}' check(cardinality(workdays)>0 and workdays <@ array[0,1,2,3,4,5,6]),
 created_at timestamptz not null default now(),
 check(end_date is null or end_date>=join_date)
);
create table public.leaves (
 id uuid primary key default gen_random_uuid(), employee_id uuid not null references public.employees(id),
 start_date date not null, end_date date not null, portion text not null check(portion in ('full','half')),
 status text not null default 'approved' check(status in ('approved','cancelled')), note text not null default '' check(length(note)<=300),
 created_at timestamptz not null default now(), check(end_date>=start_date)
);
create table public.holidays (
 id uuid primary key default gen_random_uuid(), work_date date not null,
 name text not null check(length(trim(name)) between 1 and 120), country text
);
create table public.updates (
 id uuid primary key default gen_random_uuid(), employee_id uuid not null references public.employees(id),
 work_date date not null, kind text not null check(kind in ('midday','eod')),
 progress text not null check(length(trim(progress)) between 10 and 6000),
 next_steps text not null check(length(trim(next_steps)) between 5 and 4000),
 blockers text not null check(length(trim(blockers)) between 3 and 2000),
 submitted_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 version integer not null default 1,
 unique(employee_id,work_date,kind)
);
create table public.update_versions (
 id uuid primary key default gen_random_uuid(), update_id uuid not null references public.updates(id),
 employee_id uuid not null references public.employees(id), version integer not null,
 progress text not null, next_steps text not null, blockers text not null,
 archived_at timestamptz not null default now(), unique(update_id,version)
);
create index updates_date_idx on public.updates(work_date,employee_id);
create index leaves_employee_date_idx on public.leaves(employee_id,start_date,end_date);
create index versions_update_idx on public.update_versions(update_id);

-- A verified, signed Supabase token identifies the invited account.
-- Disable public signups and enable email confirmation before inviting staff.
create function public.my_employee_id() returns uuid language sql stable security definer set search_path='' as $$
 select id from public.employees where email=lower(auth.jwt()->>'email') and active limit 1
$$;
create function public.is_hr() returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.employees where id=public.my_employee_id() and role='hr')
$$;
create function public.server_time() returns timestamptz language sql stable set search_path='' as $$ select now() $$;
revoke all on function public.my_employee_id(),public.is_hr(),public.server_time() from public;
grant execute on function public.my_employee_id(),public.is_hr(),public.server_time() to authenticated;

alter table public.employees enable row level security;
alter table public.leaves enable row level security;
alter table public.holidays enable row level security;
alter table public.updates enable row level security;
alter table public.update_versions enable row level security;
create policy employees_read on public.employees for select to authenticated using (id=public.my_employee_id() or public.is_hr());
create policy employees_insert on public.employees for insert to authenticated with check(public.is_hr());
create policy employees_edit on public.employees for update to authenticated using(public.is_hr()) with check(public.is_hr());
create policy leaves_read on public.leaves for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
create policy holidays_read on public.holidays for select to authenticated using(public.my_employee_id() is not null);
create policy updates_read on public.updates for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
create policy versions_read on public.update_versions for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
-- No direct insert/update/delete policies for updates or revisions. Use the RPC.
revoke all on public.employees,public.leaves,public.holidays,public.updates,public.update_versions from anon,authenticated;
grant select on public.employees,public.leaves,public.holidays,public.updates,public.update_versions to authenticated;
grant insert,update on public.employees to authenticated;

create function public.protect_own_hr() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if old.id=public.my_employee_id() and old.role='hr' and (new.role<>'hr' or not new.active or new.email<>old.email) then
 raise exception 'You cannot remove your own HR access'; end if;
 return new;
end $$;
create trigger employee_own_hr before update on public.employees for each row execute function public.protect_own_hr();

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

-- Apply to the existing v2 schema. Preserves employee/update/leave records.
begin;
create table public.work_sessions (
 id uuid primary key default gen_random_uuid(), employee_id uuid not null references public.employees(id),
 work_date date not null, started_at timestamptz not null default now(), ended_at timestamptz,
 break_seconds numeric not null default 0 check(break_seconds>=0), paused_at timestamptz,
 close_reason text not null default '', needs_review boolean not null default false,
 updated_at timestamptz not null default now(), unique(employee_id,work_date),
 check(ended_at is null or ended_at>=started_at), check(ended_at is null or paused_at is null)
);
create unique index one_open_session_per_employee on public.work_sessions(employee_id) where ended_at is null;
create table public.session_events (
 id uuid primary key default gen_random_uuid(), session_id uuid not null references public.work_sessions(id),
 employee_id uuid not null references public.employees(id), actor_id uuid references public.employees(id),
 action text not null, note text not null default '', snapshot jsonb not null, created_at timestamptz not null default now()
);
create table public.midday_exceptions (
 id uuid primary key default gen_random_uuid(), employee_id uuid not null references public.employees(id),
 work_date date not null, category text not null check(category in ('Work pressure','Meeting or client call','Connectivity or power issue','Other')),
 reason text not null check(length(trim(reason)) between 10 and 2000),
 status text not null default 'pending' check(status in ('pending','accepted','declined')),
 review_note text not null default '', reviewed_by uuid references public.employees(id), reviewed_at timestamptz,
 submitted_at timestamptz not null default now(), unique(employee_id,work_date)
);
create table public.exception_events (
 id uuid primary key default gen_random_uuid(), exception_id uuid not null references public.midday_exceptions(id),
 employee_id uuid not null references public.employees(id), actor_id uuid references public.employees(id),
 snapshot jsonb not null, created_at timestamptz not null default now()
);
create index session_employee_date on public.work_sessions(employee_id,work_date);
create index session_events_session on public.session_events(session_id);
alter table public.work_sessions enable row level security;
alter table public.session_events enable row level security;
alter table public.midday_exceptions enable row level security;
alter table public.exception_events enable row level security;
create policy session_read on public.work_sessions for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
create policy session_event_read on public.session_events for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
create policy exception_read on public.midday_exceptions for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
create policy exception_event_read on public.exception_events for select to authenticated using(employee_id=public.my_employee_id() or public.is_hr());
revoke all on public.work_sessions,public.session_events,public.midday_exceptions,public.exception_events from anon,authenticated;
grant select on public.work_sessions,public.session_events,public.midday_exceptions,public.exception_events to authenticated;

create function public.session_seconds(s public.work_sessions) returns numeric language sql stable set search_path='' as $$
 select greatest(0,extract(epoch from (coalesce(s.ended_at,now())-s.started_at))-s.break_seconds-case when s.paused_at is not null then greatest(0,extract(epoch from (now()-s.paused_at))) else 0 end)
$$;
create function public.check_workday(p_employee uuid,p_date date,p_kind text default 'eod') returns void language plpgsql stable security definer set search_path='' as $$
declare e public.employees;
begin
 select * into e from public.employees where id=p_employee;
 if e.id is null or not e.active then raise exception 'Active employee required'; end if;
 if p_date is null or p_date>(now() at time zone e.timezone)::date or p_date<e.join_date or (e.end_date is not null and p_date>e.end_date) then raise exception 'Outside valid employment dates'; end if;
 if not(extract(dow from p_date)::integer=any(e.workdays)) then raise exception 'This is not a configured workday'; end if;
 if exists(select 1 from public.holidays where work_date=p_date and (country is null or country=e.country)) then raise exception 'This is an imported holiday'; end if;
 if exists(select 1 from public.leaves where employee_id=e.id and status='approved' and p_date between start_date and end_date and (portion='full' or (portion='half' and p_kind='midday'))) then raise exception 'Exempt due to approved HR portal leave'; end if;
end $$;
revoke all on function public.check_workday(uuid,date,text) from public;

create function public.work_action(p_action text,p_note text default '') returns public.work_sessions language plpgsql security definer set search_path='' as $$
declare e public.employees;s public.work_sessions;d date;seconds numeric;before_state jsonb;
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
   if (seconds<28800 or now()-s.started_at>interval '18 hours') and length(trim(p_note))<10 then raise exception 'A short-day / forgotten-sign-out reason is required'; end if;
   update public.work_sessions set ended_at=now(),break_seconds=break_seconds+case when paused_at is null then 0 else extract(epoch from now()-paused_at) end,paused_at=null,close_reason=trim(p_note),needs_review=(seconds<28800 or now()-started_at>interval '18 hours'),updated_at=now() where id=s.id returning * into s;
  else raise exception 'Invalid work action'; end if;
 end if;
 insert into public.session_events(session_id,employee_id,actor_id,action,note,snapshot) values(s.id,e.id,e.id,p_action,left(trim(p_note),2000),jsonb_build_object('before',before_state,'after',to_jsonb(s)));
 return s;
end $$;
revoke all on function public.work_action(text,text) from public;
grant execute on function public.work_action(text,text) to authenticated;

create function public.submit_midday_exception(p_work_date date,p_category text,p_reason text) returns public.midday_exceptions language plpgsql security definer set search_path='' as $$
declare eid uuid;ex public.midday_exceptions;
begin
 eid=public.my_employee_id();perform public.check_workday(eid,p_work_date,'midday');
 perform pg_advisory_xact_lock(hashtextextended(eid::text||p_work_date::text,1));
 if not exists(select 1 from public.work_sessions where employee_id=eid and work_date=p_work_date) then raise exception 'Sign in to your working day first'; end if;
 if exists(select 1 from public.updates where employee_id=eid and work_date=p_work_date and kind='midday') then raise exception 'A Mid-day update already exists'; end if;
 select * into ex from public.midday_exceptions where employee_id=eid and work_date=p_work_date for update;
 if ex.id is not null then insert into public.exception_events(exception_id,employee_id,actor_id,snapshot) values(ex.id,eid,eid,to_jsonb(ex)); end if;
 insert into public.midday_exceptions(employee_id,work_date,category,reason) values(eid,p_work_date,p_category,trim(p_reason))
 on conflict(employee_id,work_date) do update set category=excluded.category,reason=excluded.reason,status='pending',review_note='',reviewed_by=null,reviewed_at=null
 returning * into ex;return ex;
end $$;
revoke all on function public.submit_midday_exception(date,text,text) from public;
grant execute on function public.submit_midday_exception(date,text,text) to authenticated;

create function public.review_midday_exception(p_id uuid,p_status text,p_note text) returns void language plpgsql security definer set search_path='' as $$
declare ex public.midday_exceptions;
begin
 if not public.is_hr() then raise exception 'HR access required'; end if;
 if p_status not in ('accepted','declined') or p_status is null or length(trim(p_note))<5 then raise exception 'Choose a review outcome and add a note'; end if;
 select * into ex from public.midday_exceptions where id=p_id for update;
 if ex.id is null then raise exception 'Exception not found'; end if;
 insert into public.exception_events(exception_id,employee_id,actor_id,snapshot) values(ex.id,ex.employee_id,public.my_employee_id(),to_jsonb(ex));
 update public.midday_exceptions set status=p_status,review_note=trim(p_note),reviewed_by=public.my_employee_id(),reviewed_at=now() where id=p_id;
end $$;
revoke all on function public.review_midday_exception(uuid,text,text) from public;
grant execute on function public.review_midday_exception(uuid,text,text) to authenticated;

-- HR corrections are audited; employees never directly write clocks.
create function public.correct_work_session(p_employee_id uuid,p_work_date date,p_started_at timestamptz,p_ended_at timestamptz,p_break_seconds numeric,p_reason text) returns public.work_sessions language plpgsql security definer set search_path='' as $$
declare s public.work_sessions;old_state jsonb;
begin
 if not public.is_hr() then raise exception 'HR access required'; end if;
 if length(trim(p_reason))<10 or p_reason is null then raise exception 'A correction reason is required'; end if;
 perform public.check_workday(p_employee_id,p_work_date,'eod');
 if p_started_at is null or p_started_at>now() or (p_started_at at time zone (select timezone from public.employees where id=p_employee_id))::date<>p_work_date or (p_ended_at is not null and (p_ended_at<p_started_at or p_ended_at>now())) or p_break_seconds is null or p_break_seconds<0 or p_break_seconds>extract(epoch from coalesce(p_ended_at,now())-p_started_at) then raise exception 'Invalid corrected clock values'; end if;
 perform pg_advisory_xact_lock(hashtextextended(p_employee_id::text,0));
 select * into s from public.work_sessions where employee_id=p_employee_id and work_date=p_work_date for update;old_state=to_jsonb(s);
 insert into public.work_sessions(employee_id,work_date,started_at,ended_at,break_seconds,close_reason,needs_review) values(p_employee_id,p_work_date,p_started_at,p_ended_at,p_break_seconds,trim(p_reason),false)
 on conflict(employee_id,work_date) do update set started_at=excluded.started_at,ended_at=excluded.ended_at,break_seconds=excluded.break_seconds,paused_at=null,close_reason=excluded.close_reason,needs_review=false,updated_at=now()
 returning * into s;
 insert into public.session_events(session_id,employee_id,actor_id,action,note,snapshot) values(s.id,p_employee_id,public.my_employee_id(),'hr_correction',trim(p_reason),jsonb_build_object('before',old_state,'after',to_jsonb(s)));
 return s;
end $$;
revoke all on function public.correct_work_session(uuid,date,timestamptz,timestamptz,numeric,text) from public;
grant execute on function public.correct_work_session(uuid,date,timestamptz,timestamptz,numeric,text) to authenticated;

create or replace function public.submit_update(p_work_date date,p_kind text,p_progress text,p_next_steps text,p_blockers text)
returns public.updates language plpgsql security definer set search_path='' as $$
declare eid uuid;prev public.updates;result public.updates;
begin
 eid=public.my_employee_id();if p_kind not in ('midday','eod') or p_kind is null then raise exception 'Invalid update type'; end if;
 perform public.check_workday(eid,p_work_date,p_kind);
 if not exists(select 1 from public.work_sessions where employee_id=eid and work_date=p_work_date) then raise exception 'A work sign-in is required. Ask HR to correct a missed sign-in'; end if;
 perform pg_advisory_xact_lock(hashtextextended(eid::text||p_work_date::text,1));
 if p_kind='eod' and exists(select 1 from public.work_sessions w where w.employee_id=eid and w.work_date=p_work_date and public.session_seconds(w)<28800 and length(trim(w.close_reason))<10) then raise exception 'Reach 8 net working hours or record a short-day reason first'; end if;
 if p_kind='eod' and not exists(select 1 from public.updates where employee_id=eid and work_date=p_work_date and kind='midday') and not exists(select 1 from public.midday_exceptions where employee_id=eid and work_date=p_work_date and status in ('pending','accepted')) and not exists(select 1 from public.leaves where employee_id=eid and status='approved' and portion='half' and p_work_date between start_date and end_date) then raise exception 'Submit your Mid-day update or a reason for missing it before EOD'; end if;
 select * into prev from public.updates where employee_id=eid and work_date=p_work_date and kind=p_kind for update;
 if prev.id is not null then
 insert into public.update_versions(update_id,employee_id,version,progress,next_steps,blockers) values(prev.id,eid,prev.version,prev.progress,prev.next_steps,prev.blockers);
 update public.updates set progress=trim(p_progress),next_steps=trim(p_next_steps),blockers=trim(p_blockers),updated_at=now(),version=version+1 where id=prev.id returning * into result;
 else
 insert into public.updates(employee_id,work_date,kind,progress,next_steps,blockers) values(eid,p_work_date,p_kind,trim(p_progress),trim(p_next_steps),trim(p_blockers)) returning * into result;
 end if;return result;
end $$;
commit;
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

-- v4 to v5: explicit management read access; HR retains administration.
begin;
alter table public.employees drop constraint employees_role_check;
alter table public.employees add constraint employees_role_check check(role in ('employee','hr','management'));
create or replace function public.can_view_team() returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.employees where id=public.my_employee_id() and role in ('hr','management'))
$$;
revoke all on function public.can_view_team() from public;
grant execute on function public.can_view_team() to authenticated;
drop policy employees_read on public.employees;
create policy employees_read on public.employees for select to authenticated using (id=public.my_employee_id() or public.can_view_team());
drop policy leaves_read on public.leaves;
create policy leaves_read on public.leaves for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy updates_read on public.updates;
create policy updates_read on public.updates for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy versions_read on public.update_versions;
create policy versions_read on public.update_versions for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy session_read on public.work_sessions;
create policy session_read on public.work_sessions for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy session_event_read on public.session_events;
create policy session_event_read on public.session_events for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy exception_read on public.midday_exceptions;
create policy exception_read on public.midday_exceptions for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
drop policy exception_event_read on public.exception_events;
create policy exception_event_read on public.exception_events for select to authenticated using (employee_id=public.my_employee_id() or public.can_view_team());
commit;
