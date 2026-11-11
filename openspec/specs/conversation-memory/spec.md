# conversation-memory Specification

## Purpose
Keep long conversations within budget without losing what the user said, given that the form state itself is rebuilt from the config every turn and never needs summarizing.

## Requirements

### Requirement: Compaction above a threshold
When the history exceeds `max_history_tokens` (default 60 000; `None` disables), the system SHALL keep the last `keep_turns` user turns (default 4) verbatim and replace older turns with a conversation memory written by a configurable (cheap) model. A failed compaction SHALL not block the turn.

#### Scenario: Long chat
- **WHEN** the history grows past the threshold
- **THEN** a `memory_compacted` event is emitted and the model's next call contains a `<conversation_memory>` block and only the recent turns

### Requirement: What the memory keeps
The memory SHALL contain the user's goal; facts the user gave with exact values and whether each is in the form or not yet (and why); decisions and preferences; rejected proposals; and open questions. It SHALL be merged with the previous memory and SHALL not describe the form's state.

#### Scenario: Value for a locked step survives
- **WHEN** the user gave a code word for a locked tab early in the chat and the chat was compacted
- **THEN** the agent still fills the code word once the tab unlocks

### Requirement: Compaction keeps the history valid
Kept turns SHALL have provider reasoning blocks removed, the memory SHALL be prepended to the first kept user message, and the frozen system prompt SHALL not be edited.

#### Scenario: Reasoning bound to an old prefix
- **WHEN** a kept assistant turn had a reasoning block
- **THEN** the block is removed before the next model call
