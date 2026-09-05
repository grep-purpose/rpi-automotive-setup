import xbmc
import xbmcaddon

# Aktiviere das Addon explizit und setze es als aktiven Provider
xbmc.executebuiltin('SetProperty(WeatherProvider,weather.multi,home)')
xbmc.executebuiltin('Weather.Refresh')
xbmc.executebuiltin('RunAddon(weather.multi)')
