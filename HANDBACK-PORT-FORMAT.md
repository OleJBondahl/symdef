HAND-BACK feat/v028: green, 3469/0
Tip: see `git log -1` (22aba27 plus this file's commit). Base f0f9cdf.
CI: `just ci` exit 0, "3469 passed", coverage 100% (log /tmp/claude-1000/ci.log).
Probes (FAILED ids): test_table.py::test_table_reads_the_given_port_format; test_edge_pattern.py::test_pattern_ports_reads_the_given_port_format; test_fitted.py::test_fitted_table_reads_the_given_port_format; test_port_format.py::test_the_library_and_its_bundle_carry_the_format (bundle skips key); test_accessors.py::test_pole_port_fills_the_given_format.
Choices: Library.port_format added (R613 B2), bundle carries optional "port_format" (validated); gate 3 skipped when none declared; table/pattern_ports/fitted_table take required kw `port_format` (callers pass library.port_format); table slots now follow the format too; format_port merged into pole_port. Guide fixture library.toml (and GUIDE/HTML copies) declare the key.
Literals left: only in docstring/error-message examples, HTML docs, tests, and the fixture/guide library.toml data. Leftover uncommitted files not mine: none (the 23 were this work).
Written by me; no subagents; no skills.
