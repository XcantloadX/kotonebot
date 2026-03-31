import bisect
import json
from pathlib import Path

from pydantic import BaseModel, Field

from ..diagnostics.codes import META_FILE_PARSE_ERROR
from ..diagnostics.models import Diagnostic
from .models import DefinitionModel, MetaModel
from .parser import MetaValidationError, parse_meta_text


class SourceRange(BaseModel):
    line: int
    column: int
    end_line: int
    end_column: int


class MetaRangeMap(BaseModel):
    definitions: SourceRange
    definitions_by_id: dict[str, SourceRange]
    fields_by_key: dict[tuple[str, str], SourceRange]

    def of_definition(self, definition_id: str) -> SourceRange:
        value = self.definitions_by_id.get(definition_id)
        if value is None:
            raise ValueError(f"Definition range not found: {definition_id}")
        return value

    def of_field(self, definition_id: str, field_name: str) -> SourceRange:
        value = self.fields_by_key.get((definition_id, field_name))
        if value is None:
            raise ValueError(f"Field range not found: {definition_id}.{field_name}")
        return value


class ParsedMetaDoc(BaseModel):
    meta_path: str
    image_path: str
    data: MetaModel
    ranges: MetaRangeMap


class MetaCorpus(BaseModel):
    docs: list[ParsedMetaDoc] = Field(default_factory=list)

    @property
    def definition_refs(self) -> list[tuple[str, str, DefinitionModel]]:
        refs: list[tuple[str, str, DefinitionModel]] = []
        for doc in self.docs:
            for definition_id, definition in doc.data.definitions.items():
                refs.append((doc.meta_path, definition_id, definition))
        return refs


def build_corpus_from_meta_paths(meta_paths: list[str]) -> tuple[MetaCorpus, list[Diagnostic]]:
    docs: list[ParsedMetaDoc] = []
    diagnostics: list[Diagnostic] = []
    for meta_path in sorted(meta_paths):
        path = Path(meta_path).resolve()
        text = path.read_text(encoding="utf-8")
        try:
            data = parse_meta_text(text)
            source_index = _build_source_index(text=text, data=data)
            docs.append(
                ParsedMetaDoc(
                    meta_path=path.as_posix(),
                    image_path=path.with_suffix("").as_posix(),
                    data=data,
                    ranges=source_index,
                )
            )
        except json.JSONDecodeError as exc:
            diagnostics.append(
                Diagnostic(
                    code=META_FILE_PARSE_ERROR.code,
                    message=str(exc),
                    meta_path=path.as_posix(),
                    severity="error",
                    line=exc.lineno,
                    column=exc.colno,
                    end_line=exc.lineno,
                    end_column=exc.colno + 1,
                )
            )
        except MetaValidationError as exc:
            location = _locate_validation_error(text=text, field_path=exc.field_path)
            diagnostics.append(
                Diagnostic(
                    code=META_FILE_PARSE_ERROR.code,
                    message=str(exc),
                    meta_path=path.as_posix(),
                    severity="error",
                    line=location.line,
                    column=location.column,
                    end_line=location.end_line,
                    end_column=location.end_column,
                )
            )
    return MetaCorpus(docs=docs), diagnostics


def _build_source_index(*, text: str, data: MetaModel) -> MetaRangeMap:
    line_offsets = _line_offsets(text)
    definitions_token = json.dumps("definitions", ensure_ascii=False)
    definitions_offset = _find_key(text=text, token=definitions_token, start=0)
    definitions_range = _range_from_offsets(
        line_offsets=line_offsets,
        start=definitions_offset,
        end=definitions_offset + len(definitions_token),
    )

    definition_ranges: dict[str, SourceRange] = {}
    field_ranges: dict[tuple[str, str], SourceRange] = {}
    definition_starts: list[tuple[str, int]] = []

    cursor = definitions_offset
    for definition_id in data.definitions.keys():
        token = json.dumps(definition_id, ensure_ascii=False)
        offset = _find_key(text=text, token=token, start=cursor)
        definition_starts.append((definition_id, offset))
        definition_ranges[definition_id] = _range_from_offsets(
            line_offsets=line_offsets,
            start=offset,
            end=offset + len(token),
        )
        cursor = offset + len(token)

    for index, (definition_id, start_offset) in enumerate(definition_starts):
        end_offset = len(text)
        if index + 1 < len(definition_starts):
            end_offset = definition_starts[index + 1][1]
        definition = data.definitions[definition_id]
        for field_name in definition.model_fields_set:
            token = _field_token(field_name)
            field_offset = _find_key_in_range(text=text, token=token, start=start_offset, end=end_offset)
            field_ranges[(definition_id, field_name)] = _range_from_offsets(
                line_offsets=line_offsets,
                start=field_offset,
                end=field_offset + len(token),
            )

    return MetaRangeMap(
        definitions=definitions_range,
        definitions_by_id=definition_ranges,
        fields_by_key=field_ranges,
    )


def _locate_validation_error(*, text: str, field_path: str | None) -> SourceRange:
    line_offsets = _line_offsets(text)
    if field_path is None or field_path.strip() == "":
        return SourceRange(line=1, column=1, end_line=1, end_column=1)
    token = json.dumps(field_path.split(".")[0], ensure_ascii=False)
    try:
        offset = _find_key(text=text, token=token, start=0)
    except ValueError:
        return SourceRange(line=1, column=1, end_line=1, end_column=1)
    return _range_from_offsets(
        line_offsets=line_offsets,
        start=offset,
        end=offset + len(token),
    )


def _field_token(field_name: str) -> str:
    if field_name == "display_name":
        return json.dumps("displayName", ensure_ascii=False)
    return json.dumps(field_name, ensure_ascii=False)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, ch in enumerate(text):
        if ch == "\n":
            offsets.append(index + 1)
    return offsets


def _range_from_offsets(*, line_offsets: list[int], start: int, end: int) -> SourceRange:
    line, column = _offset_to_line_column(line_offsets=line_offsets, offset=start)
    end_line, end_column = _offset_to_line_column(line_offsets=line_offsets, offset=end)
    return SourceRange(line=line, column=column, end_line=end_line, end_column=end_column)


def _offset_to_line_column(*, line_offsets: list[int], offset: int) -> tuple[int, int]:
    line_index = bisect.bisect_right(line_offsets, offset) - 1
    if line_index < 0:
        raise ValueError(f"Offset out of range: {offset}")
    line_start = line_offsets[line_index]
    return line_index + 1, (offset - line_start) + 1


def _find_key(*, text: str, token: str, start: int) -> int:
    offset = text.find(token, start)
    while offset >= 0:
        if _is_key_token(text=text, token=token, offset=offset):
            return offset
        offset = text.find(token, offset + len(token))
    raise ValueError(f"Key token not found: {token}")


def _find_key_in_range(*, text: str, token: str, start: int, end: int) -> int:
    offset = text.find(token, start, end)
    while offset >= 0:
        if _is_key_token(text=text, token=token, offset=offset):
            return offset
        offset = text.find(token, offset + len(token), end)
    raise ValueError(f"Key token not found in range: {token}")


def _is_key_token(*, text: str, token: str, offset: int) -> bool:
    index = offset + len(token)
    while index < len(text) and text[index] in (" ", "\t", "\r", "\n"):
        index += 1
    return index < len(text) and text[index] == ":"
