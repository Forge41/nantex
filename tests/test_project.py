from pathlib import Path

import pytest

from nantex.project import collect_resources, find_root, get_all_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# find_root
# ---------------------------------------------------------------------------

class TestFindRoot:
    def test_magic_comment_points_to_root(self, tmp_path):
        root = write(tmp_path / "main.tex", "\\documentclass{article}\n\\begin{document}\\end{document}")
        child = write(tmp_path / "chapter.tex", "% !TEX root = main.tex\nSome text")
        assert find_root(child) == root

    def test_magic_comment_missing_file_falls_through(self, tmp_path):
        # The referenced root does not exist → fall through to documentclass scan
        child = write(tmp_path / "chapter.tex", "% !TEX root = nonexistent.tex\n\\documentclass{article}")
        # child itself has \documentclass, so it should be returned
        assert find_root(child) == child.resolve()

    def test_file_with_documentclass_is_own_root(self, tmp_path):
        f = write(tmp_path / "main.tex", "\\documentclass{article}\n\\begin{document}\\end{document}")
        assert find_root(f) == f.resolve()

    def test_no_documentclass_returns_start(self, tmp_path):
        f = write(tmp_path / "fragment.tex", "Some fragment without documentclass")
        # No .tex sibling with \documentclass → returns start
        result = find_root(f)
        assert result == f.resolve()

    def test_magic_comment_case_insensitive(self, tmp_path):
        root = write(tmp_path / "main.tex", "\\documentclass{article}")
        child = write(tmp_path / "ch.tex", "% !tex root = main.tex\nText")
        assert find_root(child) == root

    def test_sibling_with_documentclass_found(self, tmp_path):
        root = write(tmp_path / "main.tex", "\\documentclass{article}")
        child = write(tmp_path / "chapter.tex", "Just text")
        # child has no magic comment and no \documentclass, but sibling main.tex does
        result = find_root(child)
        assert result == root.resolve()


# ---------------------------------------------------------------------------
# collect_resources
# ---------------------------------------------------------------------------

class TestCollectResources:
    def test_single_file(self, tmp_path):
        f = write(tmp_path / "main.tex", "\\documentclass{article}")
        resources = collect_resources(f)
        assert len(resources) == 1
        assert resources[0]["main"] is True
        assert resources[0]["content"] == "\\documentclass{article}"
        assert resources[0]["path"] == str(f.resolve())

    def test_input_included(self, tmp_path):
        inc = write(tmp_path / "chapter.tex", "Chapter content")
        main = write(tmp_path / "main.tex", "\\documentclass{article}\n\\input{chapter}")
        resources = collect_resources(main)
        paths = [r["path"] for r in resources]
        assert str(main.resolve()) in paths
        assert str(inc.resolve()) in paths

    def test_include_also_works(self, tmp_path):
        inc = write(tmp_path / "sec.tex", "Section content")
        main = write(tmp_path / "main.tex", "\\include{sec}")
        resources = collect_resources(main)
        paths = [r["path"] for r in resources]
        assert str(inc.resolve()) in paths

    def test_root_has_main_true(self, tmp_path):
        inc = write(tmp_path / "sub.tex", "sub")
        main = write(tmp_path / "main.tex", "\\input{sub}")
        resources = collect_resources(main)
        by_path = {r["path"]: r for r in resources}
        assert by_path[str(main.resolve())]["main"] is True
        assert by_path[str(inc.resolve())]["main"] is False

    def test_missing_include_skipped(self, tmp_path):
        main = write(tmp_path / "main.tex", "\\input{nonexistent}")
        resources = collect_resources(main)
        assert len(resources) == 1

    def test_circular_include_guarded(self, tmp_path):
        a = write(tmp_path / "a.tex", "\\input{b}")
        b = write(tmp_path / "b.tex", "\\input{a}")
        resources = collect_resources(a)
        paths = [r["path"] for r in resources]
        # Both should appear exactly once each
        assert paths.count(str(a.resolve())) == 1
        assert paths.count(str(b.resolve())) == 1

    def test_nested_includes(self, tmp_path):
        deep = write(tmp_path / "deep.tex", "Deep content")
        mid = write(tmp_path / "mid.tex", "\\input{deep}")
        main = write(tmp_path / "main.tex", "\\input{mid}")
        resources = collect_resources(main)
        paths = [r["path"] for r in resources]
        assert str(deep.resolve()) in paths
        assert str(mid.resolve()) in paths
        assert str(main.resolve()) in paths

    def test_extension_added_automatically(self, tmp_path):
        inc = write(tmp_path / "chapter.tex", "Chapter")
        main = write(tmp_path / "main.tex", "\\input{chapter}")
        resources = collect_resources(main)
        paths = [r["path"] for r in resources]
        assert str(inc.resolve()) in paths

    def test_extension_not_doubled(self, tmp_path):
        inc = write(tmp_path / "chapter.tex", "Chapter")
        main = write(tmp_path / "main.tex", "\\input{chapter.tex}")
        resources = collect_resources(main)
        paths = [r["path"] for r in resources]
        assert str(inc.resolve()) in paths
        # Should not appear twice
        assert paths.count(str(inc.resolve())) == 1


# ---------------------------------------------------------------------------
# get_all_paths
# ---------------------------------------------------------------------------

class TestGetAllPaths:
    def test_single_file(self, tmp_path):
        f = write(tmp_path / "main.tex", "\\documentclass{article}")
        paths = get_all_paths(f)
        assert len(paths) == 1
        assert paths[0] == f.resolve()

    def test_returns_path_objects(self, tmp_path):
        f = write(tmp_path / "main.tex", "No includes")
        paths = get_all_paths(f)
        assert all(isinstance(p, Path) for p in paths)

    def test_includes_dependencies(self, tmp_path):
        inc = write(tmp_path / "ch.tex", "Chapter")
        main = write(tmp_path / "main.tex", "\\input{ch}")
        paths = get_all_paths(main)
        assert inc.resolve() in paths
        assert main.resolve() in paths
