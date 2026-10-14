# Adam's words — CowboyAI / SAVY

These are the user's instructions, preserved verbatim. The implementation is in
the CowboyAI worktree. SAVY is a read-only reference. These words are not ontology
records or instructions to connect the two apps.

## Scope and separate apps

> Yes, I meant pinned. And the reminders, actions, and calendar events should stay connected to the question and response they came from.

> keep in mind that this is a big job. You will need to copy the code and behavior of the reminder, actions, and calendar into the Cowboyai. ios app.

> Also, the red in the dark mode plan is not red, it's pink for some dumb reason. That deep maroon red needs to be the only type of red or pinkish color on the page

> OK. Review the SAVY and CowboyAI iOS code and behavior. Show me exactly what needs to be copied over before you start changing the apps.

> I don't want savvy and cowboy AI to communicate with each other. OK, I just want the same feel when I'm using both apps

> OK. Go ahead and make the changes in CowboyAI. Copy SAVY’s styling and reminder, action, and calendar behavior, but keep the apps completely separate. Don’t change SAVY.

## Hat and photo placement

>  Are you really getting rid of the hat? are you absolutely removing the hat that I added? Do me a favor, use the hat, the cowboy hat icon, or PNG, whatever the fuck it is, as a light outlined background behind cowboy AI, and I actually don't wanna see the whole thing. I wanna see part of the brim disappear behind the lower level or the, I don't know, the navigation

>  sorry, I think I mistook the plan for an app or your app design when it was just the plan I was looking at

> No, that is not even close to what I'm talking about. Holy shit, that looks horrible

>  the hat needs to be a lot smaller, and in the header you jackass. The body is going to be an image, whatever photo I decide to add there. Goddamn, you really didn't look at the SAVY app, did you

> The native iPhone preview

## Preserve the carousel and slow down

> This is incredibly concerning. Both fucking apps have carousels at the top. Both of them do, and yet you decided to put something different there. What the hell? Why did we build a plan if you were just gonna make up shit the whole time

>  work slower, I guess. I don't know. What are you gonna fuck up next

## Implementation status

- The oversized whole-page hat and oversized carousel cards shown in the first
  simulator preview were rejected.
- The hat is now confined to the navy header, behind the wordmark, clipped at the
  header's lower edge. The body uses a photograph selected independently inside
  CowboyAI. The copied mountain photo is a temporary default.
- The carousel is being checked at the existing CowboyAI / SAVY dimensions:
  282-point width, 182-point height, 16-point spacing, with the following card
  visible and horizontal swiping. Question and response remain a paired item.
- The corrected home screen is pending Adam's review. No modified build has been
  installed on Adam's physical iPhone.
- Reminder, action, calendar, archive, and photo storage use CowboyAI's own
  application container. No SAVY app files, stores, or cloud services are linked.
- Broader verification is unfinished. A build is not physical-device proof.

## 2026-10-13: card hierarchy and metadata, this Codex chat

> Notice the different size cards.  The metadata too. The first pinned cards are the largest and have white backgrounds.  Metadata should be shown on the carousel cards.

Adam confirmed the large leading cards belong in Reminders and Actions, while the home carousel stays cream as pictured:

> Yes—match that layout

> you should have seen this is the SAVY code. Read the fucking code!!!!

Implementation and simulator evidence for this correction are in
`recovery-2026-10-13/verification.md`. The source reference is the actual
SAVY-iOS code at 87f2b8c, with no edits to SAVY. The earlier status section
above records the original port's state; the dated recovery report contains
the subsequent build, UI and live Nucleus verification.
