from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.diagnostics.codes import META_VARIANT_INVALID
from kotonebot.devtools.meta import build_corpus_from_meta_paths, build_meta_state, validate_meta_corpus
from tests.devtools._testkit import write_png_with_meta


def test_v3_policy_require_reports_missing_variant_definition():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 3,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_policy": {"en": "require", "jp": "inherit"},
                        "props": {},
                    },
                    "variant_jp": {
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
            resource_variants=["en", "jp"],
            variant_configured=True,
        )
        errors = [diag for diag in diagnostics if diag.code == META_VARIANT_INVALID.code]
        assert any("variant_policy=require requires explicit variant definition" in diag.message for diag in errors)


def test_v3_policy_exclude_reports_conflict_with_explicit_variant_definition():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 3,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_policy": {"en": "exclude", "jp": "inherit"},
                        "props": {},
                    },
                    "variant_en": {
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
        errors = [diag for diag in diagnostics if diag.code == META_VARIANT_INVALID.code]
        assert any("variant_policy=exclude forbids explicit variant definition" in diag.message for diag in errors)


def test_v3_policy_inherit_allows_missing_variant_and_merges_in_meta_state():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 3,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_policy": {"en": "inherit", "jp": "exclude"},
                        "props": {"threshold": 0.88},
                    },
                },
            },
        )
        state = build_meta_state(
            meta_paths=[meta_path.as_posix()],
            resource_variants=["en", "jp"],
            variant_configured=True,
        )
        assert all(diag.code != META_VARIANT_INVALID.code for diag in state.diagnostics)
        group = state.docs_graph.prefab_groups["ui.button"]
        assert "en" in group.merged
        assert "jp" not in group.merged


def test_v3_policy_requires_variant_policy_entries_for_configured_variants():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, meta_path = write_png_with_meta(
            root,
            "a.png",
            {
                "version": 3,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_policy": {"en": "inherit"},
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
        assert any("variant_policy is missing configured variants" in diag.message for diag in diagnostics)
