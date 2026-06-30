from typing import Literal, TypeAlias

DocSource: TypeAlias = Literal[
    "local", "sharepoint", "s3", "gcs", "azure_blob", "other"
]
