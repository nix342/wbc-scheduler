# 🎲 WBC Conflict-Free Tournament Scheduler

A personalized, priority-driven itinerary generator built specifically for the **World Boardgaming Championships (WBC)**. This application takes the massive master convention matrix and automatically cross-references it with your preferences to build a custom, mathematically optimized, zero-conflict gaming schedule using data from the official tournament schedule page.

---

## 🚀 Key Features

* **Dual Input Methods:** Build your schedule your way. Use the interactive grid to manually search and rank your **Top 10** games, or drop in a **BoardGameGeek Collection CSV** to let the algorithm find hidden gems in your library.
* **Smart Conflict Resolution:** The scheduling engine automatically filters out overlapping events, giving absolute top priority to your selected "Must-Play" titles and highest-ranked games.
* **🤖 Playoff & Variety Philosophies:** Choose between two distinct scheduling strategies:
    * *Maximize Playoff Chances:* Prioritizes repeat heats of the same game to unlock standard tournament advancement tracks.
    * *Maximize Variety:* Spreads your time across as many unique tabletop titles as possible by filtering down to single heats per game.
* **⏳ Intelligent Gap Filler:** Toggle on an aggressive third-pass algorithm that automatically scans your downtime and seamlessly drops in entry-level rounds/heats of available open games to maximize every hour of your convention trip.
* **🎨 Advanced Visual Timeline:** High-stakes playoff rounds automatically stand out on the interactive visual timeline with solid color-coded borders matching Olympic medals (Bronze for Quarterfinals, Silver for Semifinals, Gold for Finals). Special events are also explicitly color-coded (Green for Juniors, Blue for Seminars/Meetings, White for Demos) using a custom color-blind friendly palette.
* **📈 Custom Metrics Dashboard:** A dedicated stats panel that calculates real-time analytics for your generated itinerary, tracking your total gaming hours, unique titles, and your success rate for scheduling your Top 10 choices.
* **📅 Google Calendar Export:** Instantly convert your custom schedule into an explicitly formatted CSV that meets Google’s desktop import guidelines for real-time mobile push notifications on the convention floor.
* **💾 Persistent Browser Memory:** Features built-in browser local storage caching. Dial in your perfect configuration once, hit save, and your convention dates, filters, caps, and exclusions will automatically auto-load on your next visit. Includes a 1-click hard reset to instantly clear your slate.

---

## ⚙️ Advanced Algorithm Filters

To protect users from cluttered or unplayable schedules, the application includes toggleable rule-sets that operate natively inside the generator loop:
1.  **Exclude Demo Rounds:** Filters out non-competitive rule overviews.
2.  **Exclude Juniors Events:** Automatically strips out children's events.
3.  **Exclude Seminars & Meetings:** Filters down the master spreadsheet to strictly formal tournament plays by aggressively removing open gaming blocks, board meetings, and lecture sessions (events lacking formal heat structures).
4.  **Tournament Caps & Exclusions:** Set custom ceilings on specific games to drop out of brackets early, or add titles to a universal "Ban List" to ignore them entirely.

---

## 🛠️ Project Structure & Flow

The sidebar layout uses a strict hierarchy of **Progressive Disclosure** to keep the core user experience clean and intuitive while reserving complex tools for power-users:

1.  **Choose Input Method:** Search & Rank Top 10 or Upload BGG CSV.
2.  **Convention Details:** Define your exact arrival and departure windows on a 24-hour clock (e.g., Saturday at 18:00).
3.  **Priority Selector:** Lock in up to 3 absolute "Must-Play" games (like Combat Commander) to seed into the calendar first.
4.  **Filters & Preferences:** An expander menu hiding advanced tournament cap inputs, algorithm exclusions, and logic toggles.

---

## 📝 License

This project is open-source and available under the MIT License. Feel free to use, modify, and distribute it for your own gaming groups!
