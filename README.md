# 🎲 WBC 2026 Custom Tournament Scheduler

An interactive web application built with [Streamlit](https://streamlit.io/) designed to help attendees of the World Boardgaming Championships (WBC) automatically generate a personalized, conflict-free convention itinerary based on their own board game collections.

**🔗 [Access the Live App Here](https://yourname-wbc-scheduler.streamlit.app)** *(Note: Update this link with your actual Streamlit Cloud URL!)*

---

## ✨ Features

* **BGG Collection Integration:** Upload your personal BoardGameGeek (BGG) collection CSV to automatically filter the massive WBC schedule down to the games you actually know, own, and love.
* **Dynamic Priority Engine:** Flag up to 3 "Must-Play" games. The algorithm will aggressively schedule these top-tier picks first and wrap the rest of your itinerary around them.
* **Tournament Capping:** Don't want to commit to a 5-round marathon? Set early-exit caps (e.g., "Only schedule Round 1 of Combat Commander") to free up your calendar.
* **Dual Scheduling Philosophies:**
  * *The Medalist (Playoff Mode):* Prioritizes booking multiple heats of the same game to maximize your chances of advancing to the Semifinals and Finals.
  * *The Tourist (Variety Mode):* Skips duplicate heats to maximize the sheer number of unique games you get to play.
* **Travel-Aware:** Input your arrival and departure dates/times, and the app will automatically prune any events that start before you arrive or end after you need to leave.
* **CSV Export:** Download your personalized itinerary, complete with official GM and Location/Room data, straight to your device.

---

## 🚀 How to Use the App (For Attendees)

To use this scheduler, you will need a CSV export of your BoardGameGeek collection.

**How to get your BGG CSV:**
1. Log in to [BoardGameGeek.com](https://boardgamegeek.com/).
2. Go to your **Collection**.
3. Near the top right of your collection screen, click the **Download board games: CSV** link.
4. Save the file to your computer.

**Generating your Schedule:**
1. Open the [WBC Scheduler App](#).
2. Set your convention arrival and departure times in the sidebar.
3. Upload your BGG CSV file.
4. Select your "Must Play" priority games and adjust any tournament caps.
5. View your custom itinerary and click **Download Schedule as CSV** to save it!

---

## 🛠️ Local Development & Setup

If you want to run this app locally on your own machine, follow these steps:

**1. Clone the repository:**
```bash
git clone [https://github.com/yourusername/wbc-scheduler.git](https://github.com/yourusername/wbc-scheduler.git)
cd wbc-scheduler
