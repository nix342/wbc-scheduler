# 🎲 WBC Conflict-Free Tournament Scheduler

A personalized, priority-driven itinerary generator built specifically for the **World Boardgaming Championships (WBC)**. This application takes the massive master convention matrix and automatically cross-references it with your preferences to build a custom, mathematically optimized, zero-conflict gaming schedule using data from the official tournament schedule page.

---

## 🚀 Key Features

* **Dual Input Methods:** Build your schedule your way. Use the interactive grid to manually search and rank your **Top 10** games, or drop in a **BoardGameGeek Collection CSV** to let the algorithm find hidden gems in your library.
* **🤖 Playoff & Variety Philosophies:** Choose between two distinct scheduling strategies:
    * *Maximize Playoff Chances:* Prioritizes repeat heats of the same game to unlock standard tournament advancement tracks.
    * *Maximize Variety:* Spreads your time across as many unique tabletop titles as possible by filtering down to single heats per game.
* **⏳ Intelligent Gap Filler:** Toggle on an aggressive third-pass algorithm that automatically scans your downtime and seamlessly drops in entry-level rounds/heats of available open games to maximize every hour of your convention trip.
* **🎨 Advanced Visual Timeline:** High-stakes playoff rounds automatically stand out on the interactive visual timeline with solid color-coded borders matching Olympic medals (Bronze for Quarterfinals, Silver for Semifinals, Gold for Finals). Special events are explicitly color-coded (Green for Juniors, Blue for Seminars/Meetings, White for Demos) using a custom color-blind-friendly palette.
* **🏅 Convention Accolades & Smart Metrics:** The metrics dashboard goes beyond basic counts. It calculates true elapsed hours (merging overlapping playoff intervals) and generates a natural-language summary of your trip. It also awards specific "Accolades" including your Biggest Time Sink, Marathon Session, Most Variety Day, and your Biggest Time Gap (with native logic that recognizes the legendary Tuesday Morning Auction!).
* **🎒 Smart Packing List:** If you upload a BGG Collection CSV, the app cross-references your generated itinerary with your `own` status, producing a tidy checklist of exactly which games you need to pack in your suitcase.
* **📅 Google Calendar Export:** Instantly convert your custom schedule into an explicitly formatted CSV that meets Google’s desktop import guidelines for real-time mobile push notifications on the convention floor.
* **💾 Persistent Browser Memory:** Features built-in browser local storage caching. Dial in your perfect configuration once, hit save, and your convention dates, filters, caps, and exclusions will automatically auto-load on your next visit. Includes a 1-click hard reset to instantly clear your slate.

---

## ⚙️ Advanced Algorithm Filters

To protect users from cluttered or unplayable schedules, the application includes toggleable rule-sets that operate natively inside the generator loop:
1.  **Exclude Demo Rounds:** Filters out non-competitive rule overviews.
2.  **Exclude Juniors Events:** Automatically strips out children's events.
3.  **Exclude Seminars & Meetings:** Filters down the master spreadsheet to strictly formal tournament plays by aggressively removing open gaming blocks, board meetings, and lecture sessions.
4.  **Tournament Caps & Exclusions:** Set custom ceilings on specific games to drop out of brackets early, or add titles to a universal "Ban List" to ignore them entirely.

---
## 📝 License

This project is open-source and available under the MIT License. Feel free to use, modify, and distribute it for your own gaming groups!
