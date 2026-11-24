# A real booking call

A call made on the live site on November 24, 2026 (LiveKit session `RM_PiHLaYkmU4Ms`). The screenshots in the README come from this same call. The text is from the LiveKit Cloud session log, and the caller's lines are what the voice model heard, so mistakes in them are left as they were. The name, phone number and address were made up for the test.

Tool calls are shown in brackets. The ZIP check, the price and the free times come from these tools, not from the model.

---

**Agent (0:01):** Hello! I'm the virtual assistant for Draftwell. How can I help you today?

**Caller (0:10):** Hi, I'd like to book an air duct cleaning.

**Agent (0:10):** I can certainly help with that. May I please have your first name?

**Caller (0:17):** Mike Carter

**Agent (0:17):** Thank you, Mike. What is the best phone number to reach you at?

**Caller (0:27):** 4045550198

**Agent (0:27):** Got it. What is your street address, including the ZIP code? Thank you. What is your street address, including the zip code?

_The agent asked the same question twice in one turn._

**Caller (0:44):** 245 Oak Lane, 30030

_[check_service_area: the ZIP is in the service area]_

**Agent (0:45):** Thank you. How many HVAC systems are in your home?

**Caller (0:50):** Just one system.

**Agent (0:51):** And how many vents do you have in your home?

**Caller (0:55):** twelve

_[get_quote: first system with 10 vents $449, 2 extra vents $70, total estimate $519]_

**Agent (0:56):** Your estimate comes to 519 dollars. Please note that the technician confirms the final price on site. Would you like to add any dryer vent cleaning, blower cleaning, or antimicrobial treatment?

**Caller (1:12):** No, thank you.

**Agent (1:12):** What day would you prefer to schedule the cleaning?

_[find_available_slots: Tue, Nov 24, 8 AM-12 PM; Tue, Nov 24, 1 PM-5 PM; Wed, Nov 25, 8 AM-12 PM]_

**Caller (1:17):** Friday

_[find_available_slots for Friday: Fri, Nov 27, 1 PM-5 PM; Sat, Nov 28, 8 AM-12 PM; Sat, Nov 28, 1 PM-5 PM]_

**Agent (1:18):** We have availability on Friday, November 27th from 1 PM to 5 PM, and also on Saturday, November 28th from 8 AM to 12 PM or from 1 PM to 5 PM. Which would you prefer?

**Caller (1:32):** first

**Agent (1:32):** Would you like to receive the confirmation by email?

**Caller (1:37):** No, thank you.

**Agent (1:37):** Please confirm the details: Mike Carter, phone number 404-555-0198 at 245 Oak Lane, 30030, for Friday, November 27th from 1 PM to 5 PM, with an estimated price of 519 dollars, which the technician will confirm on site. Is this correct?

**Caller (2:01):** Yes, all correct.

**Agent (2:01):** One moment, I'm booking that now.

_[book_appointment: booked Fri, Nov 27, 1 PM-5 PM, total estimate $519]_

**Agent (2:04):** Everything is all set! Your appointment is booked for Friday, November 27th from 1 PM to 5 PM. Your confirmation is on its way.

**Caller (2:15):** Okay, thank you.

**Agent (2:15):** You're very welcome! Have a great day.

**Caller (2:20):** Ich habe Kreide.

_The voice model sometimes hears accented English as another language; this was a short goodbye._

**Agent (2:20):** I'm sorry, I only speak English. Could you please repeat your request in English?
