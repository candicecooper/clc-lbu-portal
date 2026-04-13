postgrest.exceptions.APIError: {'message': 'column smartar_tracking.tracked_date does not exist', 'code': '42703', 'hint': None, 'details': None}
Traceback:
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 129, in exec_func_with_error_handling
    result = func()
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 687, in code_to_exec
    _mpa_v1(self._main_script_path)
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 166, in _mpa_v1
    page.run()
    ~~~~~~~~^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/navigation/page.py", line 490, in run
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/pages/25_SMARTAR_Goal_Builder.py", line 281, in <module>
    tracking = get_tracking(goal["id"], days=21)
File "/opt/render/project/src/pages/25_SMARTAR_Goal_Builder.py", line 111, in get_tracking
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).gte("tracked_date", since).order("tracked_date").execute()
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/postgrest/_sync/request_builder.py", line 53, in execute
    raise APIError(dict(json_obj))
