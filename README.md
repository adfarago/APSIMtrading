# Case 1 trading simulation

An interactive implementation of trading in Case 1 from *Investors and Markets* by William F. Sharpe. Two investors, Mario and Hue, trade a bond and two risky assets. The app shows their portfolios, consumption, reservation prices, utility and supply-and-demand curves as trades are executed.

The app is built with Python and Shiny. It can run as a local Shiny app or be exported with ShinyLive to run in a web browser as a static site.

## Get the project

Download the repository from GitHub using **Code → Download ZIP**, then extract it. Alternatively, clone the repository with Git. Open a terminal in the extracted or cloned project folder; run all the commands below from that folder.

The main files are:

```text
app/
  app.py              Shiny interface and plots
  model.py            Simulation calculations
  requirements.txt    Additional packages for the browser app
requirements.txt      Packages for local development and export
site/                 Generated locally by the export command
```

## Set up the Python environment

Install Python if necessary. The app has been run locally with Python 3.15. Create a virtual environment and install the project's packages. Internet access is needed to download the packages.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS or Linux:**

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

If your system uses a different command to start Python, use that command for the first line. The virtual environment is local to your computer and is not included in the repository. The requirements file does not pin every package, so package versions may differ between installations.

## Run and test the local Shiny app

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m shiny run --host 127.0.0.1 --port 8000 app\app.py
```

**macOS or Linux:**

```bash
./.venv/bin/python -m shiny run --host 127.0.0.1 --port 8000 app/app.py
```

Open <http://127.0.0.1:8000/> in a browser. Keep the terminal open while using the app; press **Ctrl+C** in that terminal to stop the server.

To try the simulation, select an asset, choose a price and quantity, and click **Execute trade**. The trade-count slider can run a sequence of suggested trades. Check the tables and graphs as trades are executed, and click **Reset** to return to the starting portfolios.

## Build the ShinyLive site

Export the app after making changes to the source files. The `site/` folder is generated locally and is not included in the repository. The first export downloads the ShinyLive browser runtime and requires internet access.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\shinylive.exe export app site
```

**macOS or Linux:**

```bash
./.venv/bin/shinylive export app site
```

The `site/` folder contains the generated static website, including its browser runtime and application code. Re-export whenever the files in `app/` change; editing the source alone does not update an existing export.

## Test the ShinyLive site locally

Start a local web server from the project folder:

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m http.server 8008 --bind 127.0.0.1 --directory site
```

**macOS or Linux:**

```bash
./.venv/bin/python -m http.server 8008 --bind 127.0.0.1 --directory site
```

Open <http://127.0.0.1:8008/> and test a trade and the reset button. The first load can take a while as the browser loads Python and the app's packages. Keep the terminal open while testing and press **Ctrl+C** to stop the server. Use the local server rather than opening `site/index.html` directly: browser security restrictions prevent the app from loading correctly from a local file.

Python runs in each visitor's browser; no Python server is needed on the host. Each session is independent and is reset when the page is reloaded. The app rejects trades that would make present or future consumption zero or negative.

