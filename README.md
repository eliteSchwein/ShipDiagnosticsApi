## ShipDiagnosticsAPI
ShipDiagnosticsAPI opens a small rest api (website with a few ingame details) with real time data from your space ship, srv and more!
its primarily for streamers, specific streamer bots like mixitup or streamer bot. that way you  just send a web request to the api (default http://localhost:6009) and grab the data what you need, 
for example the state of the landing or scoop when you want to trigger a boost.

![Screenshot](/images/screenshot_1.png)

## How to install?
- head over to the release and download the latest stable release
- unzip into the EDMC Plugin Folder
- restart EDMC
- go into the settings into the Tab "ShipDiagnosticsApi"

## Settings
- port: set the port of the api server
- no proxy: if enabled all devices in the same network can access the api
- full address to the api: this is read only and is implemented for easy copy paste

### there is a mix it up example command in the plugin directory aswell. this command will disable the landing gear and scoop before boosting. after boost they change to the original state.