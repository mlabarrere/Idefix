# File-line fixture

The rule lives in `src/pkg/mod.py::compute` and reads
`src/pkg/mod.py::THRESHOLD`. A [pinned permalink](https://github.com/o/r/blob/0123456789abcdef0123456789abcdef01234567/src/pkg/mod.py#L5)
may cite a line. Times (12:30), ports (`localhost:5173`) and URLs such as
<https://example.org/mod.py:80> are not references.

```text
Traceback (most recent call last):
  File "src/pkg/mod.py", line 6, in compute
src/pkg/mod.py:6: AssertionError
```
