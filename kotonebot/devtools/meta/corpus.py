from dataclasses import dataclass, field
from pathlib import Path

from .diagnostic import Diagnostic
from .models import DefinitionV2Model, MetaV2Model
from .parser import parse_meta_file


@dataclass(slots=True)
class ParsedMetaDoc:
    meta_path: str
    image_path: str
    data: MetaV2Model


@dataclass(slots=True)
class MetaCorpus:
    docs: list[ParsedMetaDoc] = field(default_factory=list)

    @property
    def definition_refs(self) -> list[tuple[str, str, DefinitionV2Model]]:
        refs: list[tuple[str, str, DefinitionV2Model]] = []
        for doc in self.docs:
            for definition_id, definition in doc.data.definitions.items():
                refs.append((doc.meta_path, definition_id, definition))
        return refs


def build_corpus_from_meta_paths(meta_paths: list[str]) -> tuple[MetaCorpus, list[Diagnostic]]:
    docs: list[ParsedMetaDoc] = []
    diagnostics: list[Diagnostic] = []
    for meta_path in sorted(meta_paths):
        path = Path(meta_path).resolve()
        try:
            data = parse_meta_file(path)
            docs.append(
                ParsedMetaDoc(
                    meta_path=path.as_posix(),
                    image_path=path.with_suffix("").as_posix(),
                    data=data,
                )
            )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    code="META_FILE_PARSE_ERROR",
                    meta_path=path.as_posix(),
                    message=str(exc),
                )
            )
    return MetaCorpus(docs=docs), diagnostics
