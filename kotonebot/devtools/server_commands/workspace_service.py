import json
import logging
import os
import string
import uuid
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from kotonebot.devtools.server_commands.commands import (
    SERVER_COMMAND_META_REFETCH,
    SERVER_COMMAND_META_UPDATE_FILE,
    SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE,
    SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK,
    SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
    SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
    SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE,
    SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK,
    SERVER_COMMAND_VARIANT_IMPORT_IMAGE,
)
from kotonebot.devtools.server_commands.types import (
    ServerCommandResponse,
    ServerCommandRequest,
    ServerCommandSpec,
    MetaRefetchResult,
    MetaRefetchCommand,
    MetaUpdateFileCommand,
    RenameDocumentExecuteCommand,
    RenameDocumentPrecheckCommand,
    RenameSymbolExecuteCommand,
    RenameSymbolPrecheckCommand,
    RenameSymbolPrecheckResult,
    RenameSymbolExecuteResult,
    RenameSymbolTargetModel,
    VariantCloneToImageCommand,
    VariantCloneToImageResult,
    VariantCopySelectedPrefabPrecheckCommand,
    VariantCopySelectedPrefabPrecheckResult,
    VariantImportImageResult,
    VariantImportImageCommand,
)
from kotonebot.devtools.indexing.document_index_view import (
    DocumentIndexView,
    RenameDocumentExecuteResultModel,
    RenameDocumentPrecheckResultModel,
)
from kotonebot.devtools.indexing.resource_index_store import ResourceIndexStore
from kotonebot.devtools.indexing.symbol_index_view import SymbolIndexView
from kotonebot.devtools.meta import DefinitionV2Model, merge_prefab_definition, parse_meta_file
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs


class WorkspaceService:
    def __init__(self, project: Project):
        self.project = project
        self._prefabs_cache: Optional[dict[str, Any]] = None

        if project.conf is None or project.conf.editor is None or project.conf.editor.resource_path is None:
            raise ValueError("Missing [tool.kotonebot.editor.resource_path] in pyproject.toml")
        self.project_root = Path(project.conf.editor.resource_path).resolve()

        try:
            prefab_schema_for_index = self.get_prefabs_schema().get("prefabs", {})
        except Exception:
            logging.exception("Failed to preload prefab schema for index store")
            prefab_schema_for_index = {}

        self.resource_index_store = ResourceIndexStore(resource_root=self.project_root)
        self.symbol_index_view = SymbolIndexView(
            resource_root=self.project_root,
            resource_index_store=self.resource_index_store,
            prefab_schema=prefab_schema_for_index,
            resource_variants=project.conf.variant.variants if project.conf.variant and project.conf.variant.variants is not None else None,
            base_variant=project.conf.variant.base if project.conf.variant is not None else None,
            variant_configured=project.conf.variant is not None,
        )
        self.document_index_view = DocumentIndexView(
            project=project,
            resource_root=self.project_root,
            image_suffixes={".png", ".jpg", ".jpeg", ".bmp", ".webp"},
            resource_index_store=self.resource_index_store,
        )
        self.image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        self.variant_path_placeholders = {
            "variant_name",
            "file_name",
            "file_name_ext",
            "file_ext",
            "file_dir",
        }

    def list_server_commands(self) -> list[ServerCommandSpec]:
        return [
            ServerCommandSpec(id=SERVER_COMMAND_META_REFETCH, title="Refetch meta index and diagnostics", args_schema={}),
            ServerCommandSpec(id=SERVER_COMMAND_META_UPDATE_FILE, title="Update one meta file in index", args_schema={"metaPath": "string"}),
            ServerCommandSpec(
                id=SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK,
                title="Precheck grouped document rename",
                args_schema={"sourceImagePath": "string", "targetImagePath": "string"},
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE,
                title="Execute grouped document rename",
                args_schema={"sourceImagePath": "string", "targetImagePath": "string"},
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
                title="Precheck symbol rename and collect impacted variants",
                args_schema={"metaPath": "string", "definitionId": "string", "newName": "string"},
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
                title="Execute symbol rename and apply to all variants",
                args_schema={"metaPath": "string", "definitionId": "string", "newName": "string"},
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE,
                title="Clone variant definitions to target image",
                args_schema={
                    "sourceMetaPath": "string",
                    "targetImagePath": "string",
                    "variant": "string",
                    "forceOverwrite": "bool",
                },
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_VARIANT_IMPORT_IMAGE,
                title="Import variant image",
                args_schema={"baseImagePath": "string", "variant": "string", "imageDataBase64": "string", "deleteExistingTarget": "bool"},
            ),
            ServerCommandSpec(
                id=SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK,
                title="Precheck copy selected prefab to variant",
                args_schema={
                    "sourceMetaPath": "string",
                    "sourceDefinitionId": "string",
                    "baseImagePath": "string",
                    "variant": "string",
                },
            ),
        ]

    def execute_server_command(self, request: ServerCommandRequest) -> ServerCommandResponse:
        if isinstance(request, MetaRefetchCommand):
            return MetaRefetchResult(
                index=self.get_meta_index(),
                diagnostics=self.get_meta_diagnostics(),
            )
        if isinstance(request, MetaUpdateFileCommand):
            return self.update_meta_index(request.args.metaPath)
        if isinstance(request, RenameDocumentPrecheckCommand):
            return self.precheck_rename_document(
                source_image_path=request.args.sourceImagePath,
                target_image_path=request.args.targetImagePath,
            )
        if isinstance(request, RenameDocumentExecuteCommand):
            return self.execute_rename_document(
                source_image_path=request.args.sourceImagePath,
                target_image_path=request.args.targetImagePath,
            )
        if isinstance(request, RenameSymbolPrecheckCommand):
            return self.precheck_rename_symbol(
                source_meta_path=request.args.metaPath,
                source_definition_id=request.args.definitionId,
                new_name=request.args.newName,
            )
        if isinstance(request, RenameSymbolExecuteCommand):
            return self.execute_rename_symbol(
                source_meta_path=request.args.metaPath,
                source_definition_id=request.args.definitionId,
                new_name=request.args.newName,
            )
        if isinstance(request, VariantCloneToImageCommand):
            result = self.clone_variant_to_image(
                source_meta_path=request.args.sourceMetaPath,
                target_image_path=request.args.targetImagePath,
                variant=request.args.variant,
                force_overwrite=request.args.forceOverwrite,
            )
            return VariantCloneToImageResult(**result)
        if isinstance(request, VariantImportImageCommand):
            image_data = self._decode_base64(request.args.imageDataBase64)
            result = self.import_variant_image(
                base_image_path=request.args.baseImagePath,
                variant=request.args.variant,
                image_data=image_data,
                delete_existing_target=request.args.deleteExistingTarget,
            )
            return VariantImportImageResult(**result)
        if isinstance(request, VariantCopySelectedPrefabPrecheckCommand):
            result = self.precheck_copy_selected_prefab_to_variant(
                source_meta_path=request.args.sourceMetaPath,
                source_definition_id=request.args.sourceDefinitionId,
                base_image_path=request.args.baseImagePath,
                variant=request.args.variant,
            )
            return VariantCopySelectedPrefabPrecheckResult(**result)
        raise ValueError(f"Unsupported server command: {request.command}")

    def get_project_root_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"resource_root": str(self.project_root)}
        if self.project.conf and self.project.conf.editor:
            data["editor"] = self.project.conf.editor.model_dump()
        if self.project.conf and self.project.conf.variant:
            data["variant"] = self.project.conf.variant.model_dump()
        return data

    def get_prefabs_schema(self) -> dict[str, Any]:
        if self._prefabs_cache is not None:
            return self._prefabs_cache
        if not self.project.conf or not self.project.conf.editor or not self.project.conf.editor.prefabs_module:
            self._prefabs_cache = {"version": 1, "prefabs": {}}
            return self._prefabs_cache
        self._prefabs_cache = scan_prefabs(self.project.conf.editor.prefabs_module)
        if not isinstance(self._prefabs_cache, dict):
            raise ValueError("Invalid prefab schema response")
        self._prefabs_cache.setdefault("prefabs", {})
        return self._prefabs_cache

    def get_meta_index(self) -> Any:
        return self.symbol_index_view.get_snapshot_lite()

    def update_meta_index(self, meta_path: str) -> Any:
        return self.symbol_index_view.update_file(meta_path=meta_path)

    def get_meta_diagnostics(self) -> Any:
        return self.symbol_index_view.get_diagnostics()

    def get_meta_index_health(self) -> Any:
        return self.symbol_index_view.get_health()

    def precheck_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentPrecheckResultModel:
        return self.document_index_view.precheck_rename_document(
            source_image_path=source_image_path,
            target_image_path=target_image_path,
        )

    def execute_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentExecuteResultModel:
        precheck = self.precheck_rename_document(source_image_path=source_image_path, target_image_path=target_image_path)
        if precheck.hasConflicts:
            message = "\n".join(precheck.conflicts)
            raise ValueError(f"Cannot execute rename due to conflicts:\n{message}")
        renames = [(Path(item.sourcePath), Path(item.targetPath)) for item in precheck.fileRenames]
        self._execute_file_rename_batch(renames)
        return RenameDocumentExecuteResultModel(
            documents=precheck.documents,
            fileRenames=precheck.fileRenames,
            renamedFileCount=len(precheck.fileRenames),
            renamedDocumentCount=len(precheck.documents),
        )

    def precheck_rename_symbol(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        new_name: str,
    ) -> RenameSymbolPrecheckResult:
        self.symbol_index_view.ensure_ready()
        normalized_meta_path = self._normalize_path_key(str(self._get_safe_path(source_meta_path)))
        requested_name = new_name.strip()
        if requested_name == "":
            raise ValueError("newName cannot be empty")
        if source_definition_id.strip() == "":
            raise ValueError("definitionId cannot be empty")

        source_symbol = None
        for symbol in self.symbol_index_view.snapshot.symbols.values():
            if self._normalize_path_key(symbol.meta_path) == normalized_meta_path and symbol.definition_id == source_definition_id:
                source_symbol = symbol
                break
        if source_symbol is None:
            raise ValueError(f"Source symbol not found: {source_meta_path}::{source_definition_id}")

        old_name = source_symbol.name.strip()
        if old_name == "":
            raise ValueError(f"Source symbol name is empty: {source_meta_path}::{source_definition_id}")
        if requested_name == old_name:
            raise ValueError("newName must be different from oldName")

        targets_by_key: dict[tuple[str, str], RenameSymbolTargetModel] = {}
        for symbol in self.symbol_index_view.snapshot.symbols.values():
            if symbol.name != old_name:
                continue
            key = (symbol.meta_path, symbol.definition_id)
            if key in targets_by_key:
                continue
            targets_by_key[key] = RenameSymbolTargetModel(
                symbolKey=symbol.symbol_key,
                metaPath=symbol.meta_path,
                imagePath=symbol.image_path,
                definitionId=symbol.definition_id,
                variant=symbol.variant,
                type=symbol.type,
                oldName=old_name,
                newName=requested_name,
            )
        if len(targets_by_key) == 0:
            raise ValueError(f"No symbols found for name: {old_name}")

        targets = sorted(
            targets_by_key.values(),
            key=lambda item: (item.metaPath, item.definitionId),
        )
        affected_meta_count = len({item.metaPath for item in targets})

        return RenameSymbolPrecheckResult(
            sourceMetaPath=source_symbol.meta_path,
            sourceDefinitionId=source_definition_id,
            oldName=old_name,
            newName=requested_name,
            targets=targets,
            affectedMetaCount=affected_meta_count,
            affectedDefinitionCount=len(targets),
        )

    def execute_rename_symbol(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        new_name: str,
    ) -> RenameSymbolExecuteResult:
        precheck = self.precheck_rename_symbol(
            source_meta_path=source_meta_path,
            source_definition_id=source_definition_id,
            new_name=new_name,
        )

        grouped_definition_ids: dict[str, list[str]] = {}
        for item in precheck.targets:
            existing = grouped_definition_ids.get(item.metaPath)
            if existing is None:
                grouped_definition_ids[item.metaPath] = [item.definitionId]
            else:
                existing.append(item.definitionId)

        for meta_path, definition_ids in grouped_definition_ids.items():
            safe_meta_path = self._get_safe_path(meta_path)
            payload = json.loads(safe_meta_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid meta payload: {meta_path}")
            if payload.get("version") != 2:
                raise ValueError(f"Unsupported meta version for rename: {meta_path}")
            definitions = payload.get("definitions")
            if not isinstance(definitions, dict):
                raise ValueError(f"Meta definitions must be object: {meta_path}")
            for definition_id in definition_ids:
                definition = definitions.get(definition_id)
                if not isinstance(definition, dict):
                    raise ValueError(f"Definition not found: {meta_path}::{definition_id}")
                current_name = definition.get("name")
                if not isinstance(current_name, str) or current_name.strip() == "":
                    raise ValueError(f"Definition name must be non-empty string: {meta_path}::{definition_id}")
                definition["name"] = precheck.newName
            safe_meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self.symbol_index_view.build_full()

        return RenameSymbolExecuteResult(
            sourceMetaPath=precheck.sourceMetaPath,
            sourceDefinitionId=precheck.sourceDefinitionId,
            oldName=precheck.oldName,
            newName=precheck.newName,
            targets=precheck.targets,
            affectedMetaCount=precheck.affectedMetaCount,
            affectedDefinitionCount=precheck.affectedDefinitionCount,
            updatedIndexVersion=self.symbol_index_view.snapshot.index_version,
            updatedContentHash=self.symbol_index_view.snapshot.content_hash,
        )

    def clone_variant_to_image(
        self,
        *,
        source_meta_path: str,
        target_image_path: str,
        variant: str,
        force_overwrite: bool,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        source_meta = self._get_safe_path(source_meta_path)
        target_image = self._get_safe_path(target_image_path)
        if not source_meta.exists():
            raise ValueError(f"Source meta not found: {source_meta}")
        if not target_image.exists():
            raise ValueError(f"Target image not found: {target_image}")
        if not self._is_image_file(target_image):
            raise ValueError(f"Target path is not an image: {target_image}")

        target_meta_path = Path(str(target_image) + ".json")
        if target_meta_path.exists() and not force_overwrite:
            raise ValueError(f"Target meta already exists: {target_meta_path}")
        plan = self._plan_variant_clone_definitions(
            source_meta_path=source_meta,
            target_variant=variant_name,
            source_image_path=Path(str(source_meta.with_suffix(""))),
            target_image_path=target_image,
        )
        target_definitions = plan["targetDefinitions"]
        payload = {"version": 2, "definitions": target_definitions}
        target_meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"targetMetaPath": target_meta_path.as_posix(), "definitionCount": len(target_definitions)}

    def precheck_variant_import_path(
        self,
        *,
        source_meta_path: str,
        base_image_path: str,
        variant: str,
        uploaded_image_data: bytes,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        source_meta = self._get_safe_path(source_meta_path)
        base_image = self._get_safe_path(base_image_path)
        if not source_meta.exists():
            raise ValueError(f"Source meta not found: {source_meta}")
        if not base_image.exists():
            raise ValueError(f"Base image not found: {base_image}")
        if not self._is_image_file(base_image):
            raise ValueError(f"Base path is not an image: {base_image}")
        uploaded_target_image = self._decode_uploaded_image(uploaded_image_data)
        target_image_path = self._resolve_variant_import_target_path(base_image_path=base_image, variant_name=variant_name)
        plan = self._plan_variant_clone_definitions(
            source_meta_path=source_meta,
            target_variant=variant_name,
            source_image_path=Path(str(source_meta.with_suffix(""))),
            target_image_path=target_image_path,
            target_image_override=uploaded_target_image,
        )
        target_meta_path = Path(str(target_image_path) + ".json")
        return {
            "targetImagePath": target_image_path.as_posix(),
            "targetImageExists": target_image_path.exists(),
            "targetMetaPath": target_meta_path.as_posix(),
            "targetMetaExists": target_meta_path.exists(),
            "copiedDefinitions": plan["copiedDefinitions"],
            "skippedDefinitions": plan["skippedDefinitions"],
        }

    def import_variant_image(
        self,
        *,
        base_image_path: str,
        variant: str,
        image_data: bytes,
        delete_existing_target: bool,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        base_image = self._get_safe_path(base_image_path)
        if not base_image.exists():
            raise ValueError(f"Base image not found: {base_image}")
        if not self._is_image_file(base_image):
            raise ValueError(f"Base path is not an image: {base_image}")
        target_image_path = self._resolve_variant_import_target_path(base_image_path=base_image, variant_name=variant_name)
        if target_image_path.exists():
            if not delete_existing_target:
                raise ValueError(f"Target image already exists: {target_image_path}")
            target_image_path.unlink()
            target_meta_path = Path(str(target_image_path) + ".json")
            if target_meta_path.exists():
                target_meta_path.unlink()
        if len(image_data) == 0:
            raise ValueError("Import image is empty")
        target_image_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_image_path.with_suffix(target_image_path.suffix + ".tmp")
        temp_path.write_bytes(image_data)
        os.replace(temp_path, target_image_path)
        return {"targetImagePath": target_image_path.as_posix(), "size": len(image_data)}

    def precheck_copy_selected_prefab_to_variant(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        base_image_path: str,
        variant: str,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        source_meta = self._get_safe_path(source_meta_path)
        base_image = self._get_safe_path(base_image_path)
        if not source_meta.exists():
            raise ValueError(f"Source meta not found: {source_meta}")
        if not base_image.exists():
            raise ValueError(f"Base image not found: {base_image}")
        if not self._is_image_file(base_image):
            raise ValueError(f"Base path is not an image: {base_image}")
        source_meta_data = parse_meta_file(source_meta)
        source_definition = source_meta_data.definitions.get(source_definition_id)
        if source_definition is None:
            raise ValueError(f"Source definition not found: {source_definition_id}")
        if source_definition.type != "prefab":
            raise ValueError(f"Source definition is not prefab: {source_definition_id}")
        if source_definition.name is None:
            raise ValueError(f"Source definition requires name: {source_definition_id}")

        base_by_name: dict[str, DefinitionV2Model] = {}
        for definition in source_meta_data.definitions.values():
            if definition.type != "prefab" or definition.variant is not None:
                continue
            if definition.name is None:
                raise ValueError("prefab definition requires name")
            if definition.name in base_by_name:
                raise ValueError(f"duplicate prefab base definition: {definition.name}")
            base_by_name[definition.name] = definition

        target_image_path = self._resolve_variant_import_target_path(base_image_path=base_image, variant_name=variant_name)
        target_meta_path = Path(str(target_image_path) + ".json")
        target_definition_exists = False
        if target_meta_path.exists():
            target_meta_data = parse_meta_file(target_meta_path)
            target_definition_exists = source_definition_id in target_meta_data.definitions

        return {
            "targetImagePath": target_image_path.as_posix(),
            "targetImageExists": target_image_path.exists(),
            "targetMetaPath": target_meta_path.as_posix(),
            "targetMetaExists": target_meta_path.exists(),
            "targetDefinitionExists": target_definition_exists,
            "sourceDefinitionId": source_definition_id,
            "sourceDefinitionName": source_definition.name,
            "targetDefinition": self._build_prefab_variant_definition(
                definition=source_definition,
                base_by_name=base_by_name,
                target_variant=variant_name,
            ),
        }

    def copy_selected_prefab_to_variant(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        base_image_path: str,
        variant: str,
        force_overwrite: bool,
    ) -> dict[str, Any]:
        precheck = self.precheck_copy_selected_prefab_to_variant(
            source_meta_path=source_meta_path,
            source_definition_id=source_definition_id,
            base_image_path=base_image_path,
            variant=variant,
        )
        target_meta_path = self._get_safe_path(precheck["targetMetaPath"])
        target_definition = precheck["targetDefinition"]
        if not precheck["targetImageExists"]:
            raise ValueError(f"Target image not found: {precheck['targetImagePath']}")
        if precheck["targetMetaExists"]:
            target_meta_data = parse_meta_file(target_meta_path)
            target_definitions = {
                definition_id: definition.model_dump(by_alias=True, exclude_none=True)
                for definition_id, definition in target_meta_data.definitions.items()
            }
        else:
            target_definitions = {}
        if source_definition_id in target_definitions and not force_overwrite:
            raise ValueError(f"Target definition already exists: {source_definition_id}")
        target_definitions[source_definition_id] = target_definition
        payload = {"version": 2, "definitions": target_definitions}
        target_meta_path.parent.mkdir(parents=True, exist_ok=True)
        target_meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "targetImagePath": precheck["targetImagePath"],
            "targetMetaPath": precheck["targetMetaPath"],
            "definitionId": source_definition_id,
            "definitionName": precheck["sourceDefinitionName"],
            "targetDefinitionOverwritten": precheck["targetDefinitionExists"],
        }

    def _decode_base64(self, value: str) -> bytes:
        import base64

        decoded = base64.b64decode(value.encode("ascii"), validate=True)
        if len(decoded) == 0:
            raise ValueError("decoded payload is empty")
        return decoded

    def _normalize_path_key(self, path_str: str) -> str:
        return Path(path_str).resolve().as_posix().lower()

    def _execute_file_rename_batch(self, renames: list[tuple[Path, Path]]) -> None:
        staged: list[tuple[Path, Path, Path]] = []
        completed: list[tuple[Path, Path, Path]] = []
        for source, target in renames:
            temp = source.with_name(f"{source.name}.rename_tmp_{uuid.uuid4().hex}")
            if temp.exists():
                raise ValueError(f"Temporary file path already exists: {temp.as_posix()}")
            os.replace(source, temp)
            staged.append((source, temp, target))
        try:
            for source, temp, target in staged:
                os.replace(temp, target)
                completed.append((source, temp, target))
        except Exception:
            for source, _, target in reversed(completed):
                if target.exists():
                    os.replace(target, source)
            for source, temp, _ in reversed(staged):
                if temp.exists():
                    os.replace(temp, source)
            raise

    def _get_safe_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute():
            path = self.project_root / path
        resolved = path.resolve()
        try:
            resolved.relative_to(self.project_root)
        except Exception as exc:
            raise ValueError(f"Invalid path: {exc}") from exc
        return resolved

    def _is_image_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.image_suffixes

    def _assert_variant_declared(self, variant: str) -> str:
        variant_name = variant.strip()
        if variant_name == "":
            raise ValueError("variant cannot be empty")
        declared_variants = self.project.conf.variant.variants if self.project.conf.variant and self.project.conf.variant.variants is not None else []
        if variant_name not in declared_variants:
            raise ValueError(f"variant '{variant_name}' is not declared in variant.variants")
        return variant_name

    def _resolve_variant_import_target_path(self, *, base_image_path: Path, variant_name: str) -> Path:
        if self.project.conf.variant is None:
            raise ValueError("Missing [tool.kotonebot.variant] in pyproject.toml")
        variant_path_pattern = self.project.conf.variant.path_pattern
        if variant_path_pattern is None:
            raise ValueError("Missing [tool.kotonebot.variant.path_pattern] in pyproject.toml")
        rel_base_image_path = base_image_path.resolve().relative_to(self.project_root)
        declared_variants = self.project.conf.variant.variants if self.project.conf.variant.variants is not None else []
        base_variant = self.project.conf.variant.base
        base_parent_parts = list(rel_base_image_path.parent.parts)
        if base_variant is not None and len(base_parent_parts) > 0:
            head = base_parent_parts[0]
            if head == base_variant:
                base_parent_parts = base_parent_parts[1:]
            elif head in declared_variants:
                raise ValueError(f"base image path must use variant.base prefix '{base_variant}' when variant prefix exists")
        file_ext = base_image_path.suffix[1:]
        if file_ext == "":
            raise ValueError(f"base image path has no extension: {base_image_path}")
        file_dir = Path(*base_parent_parts).as_posix() if len(base_parent_parts) > 0 else ""
        if variant_path_pattern == "nest":
            rendered = f"{variant_name}/{file_dir}/{base_image_path.name}" if file_dir else f"{variant_name}/{base_image_path.name}"
        elif variant_path_pattern == "flat":
            file_name_with_variant = f"{base_image_path.stem}_{variant_name}.{file_ext}"
            rendered = f"{file_dir}/{file_name_with_variant}" if file_dir else file_name_with_variant
        elif variant_path_pattern.startswith("pattern:"):
            template = variant_path_pattern[len("pattern:"):].strip()
            if template == "":
                raise ValueError("variant.path_pattern 'pattern:' template cannot be empty")
            formatter = string.Formatter()
            for _, field_name, _, _ in formatter.parse(template):
                if field_name is None:
                    continue
                if field_name == "":
                    raise ValueError("variant.path_pattern contains empty placeholder")
                if field_name not in self.variant_path_placeholders:
                    raise ValueError(f"variant.path_pattern contains unsupported placeholder: {field_name}")
            rendered = template.format(
                variant_name=variant_name,
                file_name=base_image_path.stem,
                file_name_ext=base_image_path.name,
                file_ext=file_ext,
                file_dir=file_dir,
            ).strip()
        else:
            raise ValueError("variant.path_pattern must be 'nest', 'flat', or 'pattern: <template>'")
        if rendered == "":
            raise ValueError("variant.path_pattern resolved to empty path")
        target_image_path = self._get_safe_path(rendered)
        if target_image_path.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"target image extension is not supported: {target_image_path.suffix}")
        return target_image_path

    def _build_prefab_variant_definition(
        self,
        *,
        definition: DefinitionV2Model,
        base_by_name: dict[str, DefinitionV2Model],
        target_variant: str,
    ) -> dict[str, Any]:
        if definition.name is None:
            raise ValueError("prefab definition requires name")
        name = definition.name
        base = base_by_name.get(name)
        if base is None:
            raise ValueError(f"prefab '{name}' has no base definition")
        base_props = base.props or {}
        full = definition if definition.variant is None else merge_prefab_definition(base, definition)
        full_props = full.props or {}
        override_props: dict[str, Any] = {}
        for key, value in full_props.items():
            if key not in base_props or base_props[key] != value:
                override_props[key] = value
        output: dict[str, Any] = {"type": "prefab", "name": name, "variant": target_variant, "props": override_props}
        if full.display_name != base.display_name:
            output["displayName"] = full.display_name
        if full.description != base.description:
            output["description"] = full.description
        if full.prefab_id != base.prefab_id:
            output["prefab_id"] = full.prefab_id
        return output

    def _read_image(self, path: Path) -> Any:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {path}")
        return image

    def _decode_uploaded_image(self, image_data: bytes) -> Any:
        if len(image_data) == 0:
            raise ValueError("Import image is empty")
        decoded = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("Import image decode failed")
        return decoded

    def _validate_template_prop(self, template_prop: Any, *, definition_id: str) -> tuple[int, int, int, int]:
        if not isinstance(template_prop, dict):
            raise ValueError(f"definition '{definition_id}' props.template must be an object")
        if template_prop.get("kind") != "image":
            raise ValueError(f"definition '{definition_id}' props.template.kind must be 'image'")
        x1 = template_prop.get("x1")
        y1 = template_prop.get("y1")
        x2 = template_prop.get("x2")
        y2 = template_prop.get("y2")
        if not isinstance(x1, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.x1 must be number")
        if not isinstance(y1, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.y1 must be number")
        if not isinstance(x2, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.x2 must be number")
        if not isinstance(y2, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.y2 must be number")
        ix1 = int(x1)
        iy1 = int(y1)
        ix2 = int(x2)
        iy2 = int(y2)
        if ix2 <= ix1 or iy2 <= iy1:
            raise ValueError(f"definition '{definition_id}' props.template has invalid rect")
        return ix1, iy1, ix2, iy2

    def _extract_region(self, image: Any, rect: tuple[int, int, int, int], *, definition_id: str, image_label: str) -> Any:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = rect
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            raise ValueError(
                f"definition '{definition_id}' props.template rect is out of bounds for {image_label}: "
                f"rect=({x1},{y1},{x2},{y2}), image=({width},{height})"
            )
        return image[y1:y2, x1:x2]

    def _template_similarity_score(
        self,
        *,
        definition_id: str,
        template_prop: Any,
        source_image: Any,
        target_image: Any,
    ) -> float:
        rect = self._validate_template_prop(template_prop, definition_id=definition_id)
        source_region = self._extract_region(source_image, rect, definition_id=definition_id, image_label="source image")
        target_region = self._extract_region(target_image, rect, definition_id=definition_id, image_label="target image")
        if source_region.shape != target_region.shape:
            raise ValueError(f"definition '{definition_id}' source and target template region shape mismatch")
        match = cv2.matchTemplate(target_region, source_region, cv2.TM_CCOEFF_NORMED)
        return float(match[0][0])

    def _plan_variant_clone_definitions(
        self,
        *,
        source_meta_path: Path,
        target_variant: str,
        source_image_path: Path,
        target_image_path: Path | None,
        target_image_override: Any | None = None,
    ) -> dict[str, Any]:
        source_meta = parse_meta_file(source_meta_path)
        source_image = self._read_image(source_image_path)
        target_image = target_image_override
        if target_image is None and target_image_path is not None and target_image_path.exists():
            target_image = self._read_image(target_image_path)

        base_by_name: dict[str, DefinitionV2Model] = {}
        for definition in source_meta.definitions.values():
            if definition.type != "prefab":
                continue
            if definition.name is None:
                raise ValueError("prefab definition requires name")
            if definition.variant is None:
                if definition.name in base_by_name:
                    raise ValueError(f"duplicate prefab base definition: {definition.name}")
                base_by_name[definition.name] = definition

        target_definitions: dict[str, Any] = {}
        copied_definitions: list[dict[str, str]] = []
        skipped_definitions: list[dict[str, str]] = []
        for definition_id, definition in source_meta.definitions.items():
            definition_name = definition.name
            if definition_name is None:
                raise ValueError(f"definition '{definition_id}' requires name")
            if definition.type != "prefab":
                skipped_definitions.append({"definitionId": definition_id, "name": definition_name, "reason": "not prefab"})
                continue
            base_definition = base_by_name.get(definition_name)
            if base_definition is None:
                raise ValueError(f"prefab '{definition_name}' has no base definition")
            full_definition = definition if definition.variant is None else merge_prefab_definition(base_definition, definition)
            full_props = full_definition.props or {}
            template_prop = full_props.get("template")
            if target_image is not None and isinstance(template_prop, dict) and template_prop.get("kind") == "image":
                similarity_score = self._template_similarity_score(
                    definition_id=definition_id,
                    template_prop=template_prop,
                    source_image=source_image,
                    target_image=target_image,
                )
                if similarity_score >= 0.95:
                    skipped_definitions.append(
                        {
                            "definitionId": definition_id,
                            "name": definition_name,
                            "reason": f"same content (score={similarity_score:.4f} >= 0.95)",
                        }
                    )
                    continue
            definition_dump = self._build_prefab_variant_definition(
                definition=definition,
                base_by_name=base_by_name,
                target_variant=target_variant,
            )
            target_definitions[definition_id] = definition_dump
            copied_definitions.append({"definitionId": definition_id, "name": definition_name})

        return {
            "targetDefinitions": target_definitions,
            "copiedDefinitions": copied_definitions,
            "skippedDefinitions": skipped_definitions,
        }
