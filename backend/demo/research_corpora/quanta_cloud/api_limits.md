# Quanta Cloud API Limits

Applies to API version v3. Updated June 2026.

## Request rate limits

| Plan | Requests per minute | Burst (per 10 seconds) | Monthly API calls included |
|---|---|---|---|
| Starter | 60 | 20 | 10,000 |
| Team | 600 | 150 | 1 million |
| Business | 3000 | 600 | 10 million |
| Enterprise | 10,000 | 2,000 | unlimited |

When a limit is exceeded the API answers 429 Too Many Requests with a Retry-After header in seconds.

## Payload and file limits

| Plan | Max request body | Max file upload | Webhooks per workspace |
|---|---|---|---|
| Starter | 1 MB | 250 MB | 2 |
| Team | 10 MB | 2 GB | 20 |
| Business | 10 MB | 5 GB | 100 |
| Enterprise | 25 MB | 15 GB | 500 |

## Pagination

List endpoints return at most 100 items per page; use the cursor in the response to fetch the next page.

## Deprecation policy

An API version is supported for at least 18 months after its successor is released. Version v2 reaches end of life on 31 March 2027.

## Notes

**Note 1.** This document and the documents it refers to are the whole agreement between the parties on its subject and replace any earlier understanding.

**Note 2.** Staff are trained to explain these terms in plain language. If anything is unclear, ask for an explanation before you rely on your understanding of it.

**Note 3.** Notices must be given in writing. A notice sent through the customer portal counts as written notice from the moment it is shown as delivered.

**Note 4.** Each party will act in good faith and will cooperate reasonably with the other to give effect to the purpose of this document.
