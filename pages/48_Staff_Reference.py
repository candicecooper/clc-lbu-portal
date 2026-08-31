storage3.exceptions.StorageApiError: {'statusCode': 404, 'error': Bucket not found, 'message': Bucket not found}
Traceback:
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 136, in exec_func_with_error_handling
    result = func()
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 835, in code_to_exec
    _mpa_v1(self._main_script_path)
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 169, in _mpa_v1
    page.run()
    ~~~~~~~~^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/navigation/page.py", line 479, in run
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/pages/55_Credit_card_return.py", line 279, in <module>
    receipt_urls = upload_receipts(receipt_files, ret_staff)
File "/opt/render/project/src/pages/55_Credit_card_return.py", line 92, in upload_receipts
    sb.storage.from_(BUCKET_NAME).upload(path, file.getvalue(), {"content-type": file.type})
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/storage3/_sync/file_api.py", line 594, in upload
    return self._upload_or_update("POST", path_parts, file, file_options)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/storage3/_sync/file_api.py", line 566, in _upload_or_update
    response = self._request(
        method, ["object", self.id, *path], files=files, headers=headers, data=_data
    )
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/storage3/_sync/file_api.py", line 84, in _request
    raise StorageApiError(
        resp["message"], resp["error"], resp["statusCode"]
    ) from exc
