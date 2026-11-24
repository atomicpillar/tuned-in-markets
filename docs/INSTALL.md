# Install Tuned in Markets

Two ways: follow the steps below, or [let an AI assistant guide you](#let-an-ai-assistant-guide-you). Either way it takes about ten minutes of your time.
The program itself installs in about two minutes. The data it needs is then built by the app, in the background, the first time you run it.

You need: a Mac or a Windows computer, an internet connection and about 1 GB of free space. You do not need Git, an account or any paid tool.

## Mac

1. **Install Python.** Download the latest Python 3 from https://www.python.org/downloads/ and run the installer with the defaults.
   When it finishes, a folder opens. Double-click **Install Certificates.command** in it. Skipping this is the most common cause of "SSL certificate" errors.
2. **Get the app.** On the GitHub page click the green **Code** button, then **Download ZIP**. Double-click the ZIP in your Downloads folder to unpack it.
   You get a folder called `tuned-in-markets-main`.
3. **Open Terminal.** Press Cmd+Space, type `Terminal`, press Enter.
4. **Install.** Copy this into Terminal and press Enter:
   ```bash
   cd ~/Downloads/tuned-in-markets-main
   ```
   Then:
   ```bash
   bash install.sh
   ```
   It sets up a private Python environment inside the folder, installs the libraries, and asks for your name and email (explained below).
5. **Start it.**
   ```bash
   bash run.sh
   ```
   Your browser opens at http://localhost:8810. Keep the Terminal window open. Closing it stops the app.
6. **Next time**, open Terminal and run the same `cd` line and `bash run.sh`. To type a different command while it runs, open a new Terminal tab with Cmd+T.

## Windows

1. **Install Python.** Download the latest Python 3 from https://www.python.org/downloads/. On the first screen of the installer, tick **Add python.exe to PATH**, then choose Install Now.
2. **Get the app.** On the GitHub page click the green **Code** button, then **Download ZIP**. Right-click the ZIP and choose **Extract All**, then open the extracted folder `tuned-in-markets-main`.
3. **Install.** Double-click **install.bat**. If Windows says it protected your PC, click **More info**, then **Run anyway**. A black window installs everything and asks for your name and email.
4. **Start it.** Double-click **run.bat**. Your browser opens at http://localhost:8810. Keep the black window open. Closing it stops the app.
5. **Next time**, just double-click **run.bat**.

## The name and email question

The US securities regulator (the SEC) publishes company filings for free. In return it asks every program that fetches them to say who it is. Enter your own name and email.
They are written only to the `.env` file in the app folder on your computer, and are sent only to the SEC. If you skip it, the app asks again in your browser the first time you open the US side, and US company data waits until you answer.
India does not need it.

## What happens the first time

The first start builds five years of price history and the Swing Lab backtest. Give it 30 to 40 minutes. You can use the live parts straight away. A small orange **Warming up** note in the top bar shows it is still working. See [DAILY-USE.md](DAILY-USE.md) for what to expect on later starts.

## Optional: AI deep research

Needs your own API key and a five-minute setup: [DEEP-RESEARCH.md](DEEP-RESEARCH.md).

## Let an AI assistant guide you

Paste this into ChatGPT, Claude, Gemini or Copilot. Tell it whether you are on Mac or Windows.

```text
I want to install an open-source app called Tuned in Markets on my computer.
Its address is https://github.com/atomicpillar/tuned-in-markets
I am not technical and I use [Mac / Windows]. Please read the README and docs/INSTALL.md
in that repository first, then guide me ONE step at a time. Ask me to paste what I see after
each step. If something fails, ask for the exact error text and fix it with me.
Never ask me to paste any API key into this chat.
```

Tips for the conversation: describe what is on your screen, or paste the text of any error. Never paste your `.env` file or an API key into any chat.

## If something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| `SSL: CERTIFICATE_VERIFY_FAILED` (Mac) | Python's certificates are not installed | Open the Python folder in Applications and double-click **Install Certificates.command**, then run again |
| `python3: command not found` or "Python was not found" | Python is not installed, or not on the path | Install it from python.org. On Windows tick **Add python.exe to PATH** and run `install.bat` again |
| Nothing opens in the browser | The app is still starting | Wait 10 seconds and open http://localhost:8810 yourself |
| `Address already in use` | A copy is already running | Close the other window, or just open http://localhost:8810 |
| I typed a command and nothing happened | The window is the running app | Open a new Terminal tab (Cmd+T) for other commands |
| Parts of the page say loading for a long time | Normal during warm-up | Wait. See [DAILY-USE.md](DAILY-USE.md) |
| A data source seems blocked | A free source rate-limited you | Leave it running. That part resumes by itself in a few minutes |

## Update later

Stop the app (Ctrl+C), then run the update script. It downloads the latest version, replaces the program files and keeps your `.env`, your `data` folder and your settings.

- **Mac:** `cd ~/tuned-in-markets && bash update.sh`
- **Windows:** double-click `update.bat`

Then start the app again. If your copy is older than the update script, run this once on a Mac, and it sets itself up:

```bash
cd ~/tuned-in-markets && curl -fsSL https://raw.githubusercontent.com/atomicpillar/tuned-in-markets/main/tools/update.py -o tools/update.py && .venv/bin/python tools/update.py
```
