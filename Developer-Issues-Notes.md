Case 1: I attempted to Subscribe to an Anki Deck via Addon - Result: Subscribe Failed - No Download URL

Case 2: I deleted a previously installed Deck - Deck Management - still shows Installed and Up to date.

Case 3: I unsubscribed from a Deck - Result: Deck is still subscribed - And still gives option to Unsubscribe.

Case 4: I downloaded a 23 card deck - Result: it worked but there was a short freeze - and is bad for UX.

Case 5: I click the AnkiPH login_dialog's Forgot Password and Register Now links - No dedicated Forgot Password page or Forgot Password dialog in webapp not triggered AnD/or SignUp tab in /auth not opened.

case 6: I sign up - Deck rebuild - is slow - delayed at least 1 second.

case 7: Im on free tier limited access account - i click browse decks in deck management - and nottorney collection which is a paid deck is displayed - i click install - it sorta allows me but there is an error from case 1 - in which case IF case 1 was fixed - and downloading a paid deck did allow?? then it would be broken - because free tier accounts - cant download paid decks.

Case 8: Im not logged in- im aware of this - i click AnkiPH button in topnav - it shows me a blank Dialog that has a button Sign IN - I click it and leads me to Login_dialog - but i feel like this part is unnecessary - and interferes with user UX - because if im not logged in - why not just call Login_dialog first.

case 9: Im in deck management - logged in - i click the Browse Decks button. Browse Decks dialog shows up. Its ugly. and just a list.

case 10: im in deck management - logged in - i click the Browse decks button. browse decks dialog shows up. i can see that I am subscribed in 2 decks. I go to the Ankiph collections page where I am signed in the same account. I unsubscribe from both said decks. I recheck in anki addon. click browse decks again. But it shows that Im still subscribed to both said decks. I log out. sign in the same account - click browse decks- and it now shows that im unsubscribed to both said decks - ISSUE: no refresh in browse decks - no real-time updates- ux not good.

Case 11: Im in deck management and logged in - but in a free tier access account - i click Create AnkiPH deck - but wait - is it an AnkiPH deck - or a Collaborative Deck - THEN it shows me: "The action you are trying to perform requires an active membership. Unlock a membership here: AnkiPH Plans Or if you prefer, reach out for support at our AnkiPH Community." WHICH i notice is this message dialog is ugly - is should be beautiful and have buttons that convice the user to Subscribe to a membership plan. Instead of appearing like an error. Should have a LEARN More too - linking to a page that educates user on why membership plan is good and should be subscribed to.

case 12: MAIN Dialog UI - is ugly and confusing and jarring - and dumb.

case 13: About UI - in settigns dialog - sucks - text are hidden - and dialog needs to be stretched downward to reveal them.

Case 14: UNKNOWN STATE - whether working or not working - 1. Study Progress Sync 2. Protected Fields 3. Advanced Tab is just dumb and too confusing.


case 15: ui files i dont know the purpose for:
a. advanced_sync_dialog.py
b. history_dialog.py
c. suggestion_dialog.py
d. sync_dialog.py
e. tabbed_dialog.py

case 16: I opened deck management - clicked browse decks - then browse decks dialog opened - and it let me subscribe to a free tier deck - but after I subscribed - it automatically installed it - should this be automatic? Maybe? i think it being automatic makes it simple - but user should be informed that it will be downloaded automatically when they subscribe via either addon or webapp.

