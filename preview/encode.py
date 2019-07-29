"""JSON encoder/decoder for domain objects."""

from typing import Union, List, Any
from arxiv.util.serialize import ISO8601JSONEncoder

from . import domain


class PreviewEncoder(ISO8601JSONEncoder):
    """Extend :class:`.ISO8601JSONEncoder` to encode domain objects."""

    def default(self, obj: Any) -> Union[str, List[Any]]:
        if isinstance(obj, domain.Metadata):
            return {
                'added': obj.added.isoformat(),
                'checksum': obj.checksum,
                'size_bytes': obj.size_bytes
            }
        elif isinstance(obj, domain.Preview):
            return {
                'source_id': obj.source_id,
                'checksum': obj.checksum,
                'metadata': self.default(obj.metadata)
                    if obj.metadata is not None else None,
            }
        return super().default(obj)