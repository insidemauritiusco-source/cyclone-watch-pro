# Inside Mauritius Cyclone Watch Pro

## Preview
Open `index.html` in a browser. The included dated MMS snapshot is not live; the simulation button shows invented movement. All controls work offline except network refresh and official links.

## Live polling on a computer
Requires Python 3.10+ and internet. In this directory run `python update.py --loop` in one terminal, then `python -m http.server 8000` in another. Open http://localhost:8000. The updater retrieves official public MMS pages every five minutes while running. If retrieval or parsing fails, the dashboard displays incomplete/unverified data. The source may change or update less frequently. Do not treat this dashboard as an emergency alert system. The live network connection has not been integration-tested in the creation environment.

## GitHub Pages hosting
Create a separate public repository named `cyclone-watch-pro` with a `main` branch. Upload all files at the root, including `.github/workflows/update.yml`. In Settings > Pages choose GitHub Actions as the source, not Deploy from a branch. In Actions, open Refresh and deploy Cyclone Watch Pro and run it manually. Check the deployment and public data.json, compare the displayed observation and warning against MMS, and check the last successful refresh timestamp. The workflow requests refresh every 15 minutes, commits the observation history and explicitly deploys the public files via GitHub Pages. GitHub schedules can be delayed or disabled; a failed source request produces incomplete/unverified status. Hosting, network retrieval and workflow permissions have not been live-tested. Do not use this as an emergency warning system. No existing repository, DNS or hosting was modified.

## Data and limitations
Source: Mauritius Meteorological Services current storm and warning pages. The parser is intentionally conservative and does not generate an official class or forecast. The map is schematic, approximate distances are great-circle estimates, and storm-marker rotation is decorative, not wind data. No forecast cone or landfall prediction is fabricated. No SMS/push notification service or official radar feed is built in; the dashboard links to official sources. The warning status and timestamp require verification from MMS. For emergency decisions always follow official local authorities.
