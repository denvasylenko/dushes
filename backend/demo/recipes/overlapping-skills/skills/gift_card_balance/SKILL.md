---
name: gift_card_balance
description: How much is left on a gift card and until when it is valid. Not for refunds.
forms: [barber_booking]
tools: ["gift_card_skills_tools:check_gift_card"]
---
Ask for the code (GC-XXXX-XXXX) if it is missing, call check_gift_card and say the balance and the expiry date.
If the user then asks for their money back, use the gift_card_refund skill instead.
