def __getattr__(name):
    """Lazy loading of resgen module to avoid importing cv2 when using CLI."""
    resgen_attrs = {
        "CodeWriter",
        "ResourceNode",
        "ClassNode",
        "SchemaParser",
        "StandardGenerator",
        "ParserRegistry",
        "KotoneV1Parser",
        "BasicSpriteParser",
        "to_camel_case",
        "unify_path",
        "build_class_tree",
        "ImageProcessor",
    }
    
    if name in resgen_attrs:
        from . import resgen
        return getattr(resgen, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # core
    "CodeWriter",
    "ResourceNode",
    "ClassNode",
    "SchemaParser",

    # generator
    "StandardGenerator",

    # parsers
    "ParserRegistry",
    "KotoneV1Parser",
    "BasicSpriteParser",

    # utils
    "to_camel_case",
    "unify_path",
    "build_class_tree",
    "ImageProcessor",
]

