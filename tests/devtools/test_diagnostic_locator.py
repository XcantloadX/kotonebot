from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.meta.corpus import build_corpus_from_meta_paths


def test_build_corpus_produces_definition_and_field_ranges():
    with TemporaryDirectory() as tmp:
        meta_path = Path(tmp) / "a.png.json"
        meta_path.write_text(
            (
                '{\n'
                '  "version": 2,\n'
                '  "definitions": {\n'
                '    "btn": {\n'
                '      "type": "prefab",\n'
                '      "name": "ui.btn",\n'
                '      "variant_inherit": false,\n'
                '      "props": {}\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        corpus, diagnostics = build_corpus_from_meta_paths([meta_path.as_posix()])
        assert diagnostics == []
        assert len(corpus.docs) == 1
        doc = corpus.docs[0]
        definition_range = doc.ranges.of_definition("btn")
        field_range = doc.ranges.of_field("btn", "variant_inherit")
        assert definition_range.line == 4
        assert field_range.line == 7
        assert field_range.end_column > field_range.column
