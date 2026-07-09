"""ArtifactRegistry: the central store of every artifact produced during a compilation
run. Stages publish artifacts here and look each other's up by (type, id) instead of
importing one another directly, so stages stay decoupled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.errors import ArtifactError

ArtifactT = TypeVar("ArtifactT", bound=CompilerBaseModel)


@dataclass
class ArtifactRegistry:
    _store: dict[tuple[type, str], CompilerBaseModel] = field(default_factory=dict)

    def register(self, artifact: ArtifactT, *, artifact_id: str) -> str:
        key = (type(artifact), artifact_id)
        if key in self._store:
            raise ArtifactError(
                f"Artifact already registered: {type(artifact).__name__}/{artifact_id}",
                details={"artifact_type": type(artifact).__name__, "artifact_id": artifact_id},
            )
        self._store[key] = artifact
        return artifact_id

    def get(self, artifact_type: type[ArtifactT], artifact_id: str) -> ArtifactT:
        try:
            return self._store[(artifact_type, artifact_id)]  # type: ignore[return-value]
        except KeyError:
            raise ArtifactError(
                f"Artifact not found: {artifact_type.__name__}/{artifact_id}",
                details={"artifact_type": artifact_type.__name__, "artifact_id": artifact_id},
            ) from None

    def all(self, artifact_type: type[ArtifactT]) -> tuple[ArtifactT, ...]:
        return tuple(
            artifact
            for (stored_type, _), artifact in self._store.items()
            if stored_type is artifact_type
        )

    def __len__(self) -> int:
        return len(self._store)
