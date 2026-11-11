---
name: gift_cards
description: Check a gift card balance and explain how a gift card can pay for a booking.
forms: [barber_booking]
tools: ["demo.skill_tools:check_gift_card"]
---
When the user mentions a gift card or a voucher:
1. Ask for the card code if they have not given it (format GC-XXXX-XXXX).
2. Call check_gift_card with the code.
3. Explain the balance and the expiry date. If the balance covers the price shown in the form, say the visit can be paid fully with the card; otherwise say how much is left to pay at the salon.
4. Gift cards are applied at the salon; there is no field for them in the form. Do not try to put the code into "Comment for the barber" unless the user asks.
