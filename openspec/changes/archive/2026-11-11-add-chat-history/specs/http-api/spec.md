# Spec Delta

## ADDED Requirements

### Requirement: Thread endpoints
The router SHALL provide `GET /threads/{thread_id}` returning `{transcript, pending_card}` and `DELETE /threads/{thread_id}` removing the thread's transcript and model history. Invalid thread ids SHALL be rejected with 400.

#### Scenario: Restoring a thread
- **WHEN** a client calls `GET /threads/{thread_id}` for a thread with a pending card
- **THEN** the response contains the full transcript and that card in `pending_card`
