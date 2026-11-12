## ADDED Requirements

### Requirement: Feedback endpoint
The router SHALL accept `POST /feedback {thread_id, value: 1 | -1, card_id?}`, store it with the thread's transcript and answer 204. Other values SHALL be refused with 422.

#### Scenario: A thumbs up
- **WHEN** the client posts value 1 for a thread
- **THEN** the answer is 204 and the transcript records it

