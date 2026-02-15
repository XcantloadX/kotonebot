from __future__ import annotations

from .models import IndexedSymbol


def symbol_to_lite(symbol: IndexedSymbol) -> dict:
    return {
        "symbolKey": symbol.symbol_key,
        "definitionId": symbol.definition_id,
        "type": symbol.type,
        "name": symbol.name,
        "displayName": symbol.display_name,
        "prefabId": symbol.prefab_id,
        "metaPath": symbol.meta_path,
        "imagePath": symbol.image_path,
        "primaryGeometry": symbol.primary_geometry,
        "searchText": " ".join(symbol.search_tokens),
    }
