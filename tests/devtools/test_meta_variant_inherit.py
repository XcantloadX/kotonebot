from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.diagnostics.codes import (
    META_VARIANT_INHERIT_DISABLED,
    META_VARIANT_INHERIT_MISSING_VARIANTS,
    META_VARIANT_INHERIT_UNUSED,
)
from kotonebot.devtools.meta import build_corpus_from_meta_paths, build_meta_state, validate_meta_corpus
from tests.devtools._testkit import write_png_with_meta


def test_validate_meta_corpus_warns_base_prefab_without_variant_inherit_when_variant_configured():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    }
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["en"],
            variant_configured=True,
        )
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.code == META_VARIANT_INHERIT_DISABLED.code
        assert diag.severity == "warning"
        assert diag.definition_id == "base"
        assert "ui.button" in diag.message
        assert "::" not in diag.message
        assert ".png.json" not in diag.message


def test_validate_meta_corpus_no_warning_without_variant_configured():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    }
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["en"],
            variant_configured=False,
        )
        assert diagnostics == []


def test_validate_meta_corpus_warn_once_when_variant_inherit_set_but_project_variant_not_configured():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base_a": {
                        "type": "prefab",
                        "name": "ui.button.a",
                        "variant_inherit": True,
                        "props": {},
                    },
                    "base_b": {
                        "type": "prefab",
                        "name": "ui.button.b",
                        "variant_inherit": False,
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=None,
            variant_configured=False,
        )
        matches = [diag for diag in diagnostics if diag.code == META_VARIANT_INHERIT_UNUSED.code]
        assert len(matches) == 1


def test_validate_meta_corpus_no_warning_for_explicit_false_when_variant_configured():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": False,
                        "props": {},
                    },
                    "en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["en"],
            variant_configured=True,
        )
        assert diagnostics == []


def test_validate_meta_corpus_error_when_variant_inherit_false_and_variants_missing():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": False,
                        "props": {},
                    },
                    "en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["en", "jp"],
            variant_configured=True,
        )
        errors = [diag for diag in diagnostics if diag.code == META_VARIANT_INHERIT_MISSING_VARIANTS.code]
        assert len(errors) == 1
        assert "jp" in errors[0].message


def test_validate_meta_corpus_no_error_when_variant_inherit_false_and_variants_complete():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": False,
                        "props": {},
                    },
                    "en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {},
                    },
                    "jp": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "jp",
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["base", "en", "jp"],
            base_variant="base",
            variant_configured=True,
        )
        assert all(diag.code != META_VARIANT_INHERIT_MISSING_VARIANTS.code for diag in diagnostics)


def test_validate_meta_corpus_excludes_base_variant_from_missing_check():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": False,
                        "props": {},
                    },
                    "en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["base", "en", "jp"],
            base_variant="base",
            variant_configured=True,
        )
        errors = [diag for diag in diagnostics if diag.code == META_VARIANT_INHERIT_MISSING_VARIANTS.code]
        assert len(errors) == 1
        assert "jp" in errors[0].message
        assert "base" not in errors[0].message


def test_validate_meta_corpus_reports_when_variant_equals_base():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    },
                    "wrong": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "base",
                        "props": {},
                    },
                },
            },
        )
        corpus, parse_diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert parse_diagnostics == []
        diagnostics = validate_meta_corpus(
            corpus,
            resource_variants=["base", "en", "jp"],
            base_variant="base",
            variant_configured=True,
        )
        assert any(diag.message.startswith("variant 'base' must not be equal to base variant") for diag in diagnostics)


def test_build_meta_state_keeps_variant_group_when_only_warning_exists():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    },
                    "en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {},
                    },
                },
            },
        )
        state = build_meta_state(
            meta_paths=[meta_path.as_posix()],
            resource_variants=["en"],
            variant_configured=True,
        )
        assert any(diag.code == META_VARIANT_INHERIT_DISABLED.code for diag in state.diagnostics)
        assert "ui.button" in state.docs_graph.prefab_groups
