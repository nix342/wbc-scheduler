# 🎲 WBC Conflict-Free Tournament Scheduler

A personalized, priority-driven itinerary generator built specifically for the **World Boardgaming Championships (WBC)**. This application takes the massive master convention matrix and automatically cross-references it with a user's personal BoardGameGeek collection to build a custom, mathematically optimized, zero-conflict gaming schedule.

---

## 🚀 Key Features

* **Smart Conflict Resolution:** The scheduling engine automatically filters out overlapping events, giving absolute top priority to user-selected "Must-Play" titles and highest-rated games.
* **🤖 Playoff & Variety Philosophies:** Choose between two distinct scheduling strategies:
    * *Maximize Playoff Chances:* Prioritizes repeat heats of the same game to unlock standard tournament advancement tracks.
    * *Maximize Variety:* Spreads your time across as many unique tabletop titles as possible by filtering down to single heats per game.
* **⏳ Intelligent Gap Filler:** Toggle on an aggressive third-pass algorithm that automatically scans your downtime and seamlessly drops in entry-level rounds/heats of available open games to maximize every hour of your convention trip.
* **🏅 Medal-Tier Playoff Visuals:** High-stakes playoff rounds automatically stand out on the interactive visual timeline with crisp, solid color-coded borders matching Olympic medals (Bronze for Quarterfinals, Silver for Semifinals, Gold for Finals).
* **📈 Custom Metrics Dashboard:** A dedicated stats panel that calculates real-time analytics for your generated itinerary, including total scheduled sessions, unique games played, total gaming hours, and your lineup's average BGG rating.
* **📅 Google Calendar Export:** Instantly convert your custom schedule into an explicitly formatted CSV that meets Google’s desktop import guidelines for real-time mobile push notifications on the convention floor.
* **💾 Persistent Browser Memory:** Features built-in browser local storage caching. Dial in your perfect configuration once, hit save, and your convention dates, filters, caps, and exclusions will automatically auto-load on your next visit.

---

## ⚙️ Advanced Algorithm Filters

To protect users from cluttered or unplayable schedules, the application includes toggleable rule-sets that operate natively inside the generator loop:
1.  **Exclude Demo Rounds:** Filters out non-competitive rule overviews.
2.  **Exclude Juniors Events:** Automatically strips out children's events.
3.  **Exclude Seminars & Meetings:** Filters down the master spreadsheet to strictly formal tournament plays by aggressively removing open gaming blocks, board meetings, and lecture sessions.
4.  **Tournament Caps & Exclusions:** Set custom ceilings on specific games to drop out of brackets early, or add titles to a universal "Ban List" to ignore them entirely.

---

## 🛠️ Project Structure & Flow

The sidebar layout uses a strict hierarchy of **Progressive Disclosure** to keep the core user experience clean and intuitive while reserving complex tools for power-users:

1.  **Upload Data:** Drag-and-drop a standard BoardGameGeek personal collection CSV.
2.  **Convention Details:** Define your exact arrival and departure windows on a 24-hour clock.
3.  **Priority Selector:** Lock in up to 3 absolute "Must-Play" games to seed into the calendar first.
4.  **Filters & Preferences:** An expander menu hiding advanced tournament cap inputs, algorithm exclusions, and BGG rating cutoffs.

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE). Feel free to use, modify, and distribute it for your own gaming groups!
