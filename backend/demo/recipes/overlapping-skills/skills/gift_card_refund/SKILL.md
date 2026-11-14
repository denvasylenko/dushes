---
name: gift_card_refund
description: Refund the unused balance of a gift card when the user asks for their money back. Not for checking a balance.
forms: [barber_booking]
tools: ["gift_card_skills_tools:refund_gift_card"]
---
Only when the user asks for a refund: ask for the code if it is missing and call refund_gift_card with it. The user
confirms the refund on a card; say what happens next from the tool's answer. Never promise an amount yourself.
