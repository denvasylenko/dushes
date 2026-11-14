---
name: gift_cards
description: Check a gift card balance and explain how a gift card can pay for a booking.
forms: [barber_booking]
tools: ["gift_card_tools:check_gift_card"]
---
When the user mentions a gift card or a voucher:
1. Ask for the card code if they have not given it (format GC-XXXX-XXXX).
2. Call check_gift_card with the code.
3. Say the balance and the expiry date. If the balance covers the price shown in the form, say the visit can be
   paid fully with the card; otherwise say that the rest is paid at the salon. Never compute a price yourself:
   read it from the form.
4. Gift cards are applied at the salon; the form has no field for them.
