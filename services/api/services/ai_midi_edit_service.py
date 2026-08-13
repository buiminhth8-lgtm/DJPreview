"""T35.4 pure Proposal orchestration over the validated Transformer and Diff."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import ValidationError

from packages.music_core.midi_editing.diff import calculate_midi_note_diff
from packages.music_core.midi_editing.models import MidiEditPlan
from packages.music_core.midi_editing.plan_validator import PlanValidator
from packages.music_core.midi_editing.scope import scope_fingerprint
from packages.music_core.midi_editing.transformer import transform_midi_notes
from services.api.schemas.ai_midi_edit import (
    AiMidiEditContext,
    AiMidiEditProposal,
    AiMidiEditWarning,
    MidiNoteModification,
)


class AiMidiEditProposalErrorCode(StrEnum):
    INVALID_CONTEXT = "invalid_context"
    SNAPSHOT_IDENTITY_MISMATCH = "snapshot_identity_mismatch"
    RESULT_MISMATCH = "result_mismatch"
    INVALID_PROPOSAL_METADATA = "invalid_proposal_metadata"


class AiMidiEditProposalError(ValueError):
    """Proposal construction failed atomically before any result was returned."""

    def __init__(self, code: AiMidiEditProposalErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _snapshot_context(context: AiMidiEditContext) -> AiMidiEditContext:
    try:
        if not isinstance(context, AiMidiEditContext):
            raise TypeError("context type")
        return AiMidiEditContext.model_validate(
            context.model_dump(mode="python"),
            strict=True,
        )
    except (TypeError, ValidationError, ValueError) as error:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.INVALID_CONTEXT,
            "AiMidiEditContext contract 无效",
        ) from error


def build_midi_edit_proposal(
    context: AiMidiEditContext,
    plan: MidiEditPlan,
    seed: int,
    *,
    planner_provider: str,
    planner_model: str | None,
    prompt_version: str,
    proposal_id: UUID | None = None,
    created_at: datetime | None = None,
) -> AiMidiEditProposal:
    """Build a stateless scoped Proposal; never read or write Project state."""
    snapshot = _snapshot_context(context)
    if snapshot.scope.track_id != snapshot.track_id:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.SNAPSHOT_IDENTITY_MISMATCH,
            "Context track_id 与 Scope 不一致",
        )
    if scope_fingerprint(snapshot.scope) != snapshot.scope_fingerprint:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.SNAPSHOT_IDENTITY_MISMATCH,
            "Context scope_fingerprint 与 Scope 不一致",
        )

    validated_plan = PlanValidator.validate(plan, snapshot)
    before_notes = tuple(item.model_copy(deep=True) for item in snapshot.scoped_notes)
    transformed = transform_midi_notes(
        before_notes,
        validated_plan,
        snapshot.scope,
        ppq=snapshot.ppq,
        total_ticks=snapshot.total_ticks,
        is_drum=snapshot.is_drum,
        seed=seed,
    )
    if transformed.seed != seed:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.RESULT_MISMATCH,
            "Transformer seed 与请求 seed 不一致",
        )
    authorized_ids = tuple(item.id for item in before_notes)
    note_diff = calculate_midi_note_diff(
        before_notes,
        transformed.notes,
        authorized_note_ids=authorized_ids,
    )
    if tuple(sorted(item.id for item in note_diff.deleted)) != transformed.removed_note_ids:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.RESULT_MISMATCH,
            "Transformer removed IDs 与 Diff 不一致",
        )

    try:
        return AiMidiEditProposal(
            proposal_id=proposal_id or uuid4(),
            song_id=snapshot.song_id,
            base_version_id=snapshot.base_version_id,
            editor_session_id=snapshot.editor_session_id,
            base_draft_revision=snapshot.draft_revision,
            base_scope_revision=snapshot.scope_revision,
            scope_fingerprint=snapshot.scope_fingerprint,
            track_id=snapshot.track_id,
            track_role=snapshot.track_role,
            scope=snapshot.scope.model_copy(deep=True),
            transformer_seed=seed,
            planner_provider=planner_provider,
            planner_model=planner_model,
            prompt_version=prompt_version,
            plan=validated_plan.model_copy(deep=True),
            before_notes=[item.model_copy(deep=True) for item in note_diff.before_notes],
            after_notes=[item.model_copy(deep=True) for item in note_diff.after_notes],
            added=[item.model_copy(deep=True) for item in note_diff.added],
            deleted=[item.model_copy(deep=True) for item in note_diff.deleted],
            modified=[
                MidiNoteModification(
                    note_id=item.note_id,
                    before=item.before.model_copy(deep=True),
                    after=item.after.model_copy(deep=True),
                    changed_fields=item.changed_fields,
                )
                for item in note_diff.modified
            ],
            change_count=note_diff.change_count,
            is_noop=note_diff.is_noop,
            warnings=[
                AiMidiEditWarning(
                    code=warning.code,
                    operation_index=warning.operation_index,
                    operation_type=warning.operation_type,
                    note_id=warning.note_id,
                )
                for warning in transformed.warnings
            ],
            created_at=created_at or datetime.now(timezone.utc),
        )
    except (TypeError, ValidationError, ValueError) as error:
        raise AiMidiEditProposalError(
            AiMidiEditProposalErrorCode.INVALID_PROPOSAL_METADATA,
            "Proposal metadata/contract 无效",
        ) from error
