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
