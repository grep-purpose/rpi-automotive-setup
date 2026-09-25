from ..conversions import *

class Weather():
    def __init__():
        pass

    def get_weather(data, loc, locid):
    #current - standard
        set_property('Location'                    , loc)
        set_property('Current.Location'            , '%s, %s' % (data['location']['town'],data['location']['country']))
        set_property('Current.Condition'           , data['location']['outlook'])
        set_property('Current.Temperature'         , convert_temp(data['location']['temperature'], 'F', 'C'))
        # Yahoo liefert beim UV-Index teilweise auch nachts noch
        # einen Tages-/Forecastwert. Deshalb bestimmen wir UV
        # unabhängig vom Wetterzustand anhand von Sunrise/Sunset.
        yahoo_uv = ''
        if data['conditions']['conditions']['uv']:
            yahoo_uv = str(
                data['conditions']['conditions']['uv']['value']
            )

        uv_now = yahoo_uv

        try:
            # Aktuelle Ortszeit grob aus dem ersten echten Hourly-Eintrag ableiten.
            uv_approxtime = None

            if len(data['forecasts'][0]['conditionsForecasts']) > 1:
                for uv_item in data['forecasts'][0]['conditionsForecasts']:
                    if (
                        uv_item['time'] == 'Now'
                        or uv_item['text'] == 'Sunrise'
                        or uv_item['text'] == 'Sunset'
                    ):
                        continue

                    uv_approxtime = uv_item['time']
                    break

            if uv_approxtime:
                if uv_approxtime == 'Midnight':
                    uv_approxtime = '12 AM'
                elif uv_approxtime == 'Noon':
                    uv_approxtime = '12 PM'

                uv_hour = (
                    time.strptime(
                        uv_approxtime,
                        '%I %p'
                    ).tm_hour - 1
                ) % 24

                uv_sunrise = time.strptime(
                    data['location']['sunrise'],
                    '%I:%M %p'
                ).tm_hour

                uv_sunset = time.strptime(
                    data['location']['sunset'],
                    '%I:%M %p'
                ).tm_hour

                if uv_hour < uv_sunrise or uv_hour >= uv_sunset:
                    uv_now = '0'

        except Exception:
            pass

        set_property('Current.UVIndex', uv_now)
        if  data['conditions']['conditions']['airQuality']:
            set_property('Current.AirQuality'          , data['conditions']['conditions']['airQuality']['value'] + ' UAQI')
        else:
            set_property('Current.AirQuality'              , '')
        if  data['conditions']['conditions']['pollen']:
            set_property('Current.Pollen'              , data['conditions']['conditions']['pollen']['value'])
        else:
            set_property('Current.Pollen'              , '')
        if data['location']['outlook'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
            # yahoo does not tell if this current icon refers to day or nighttime, nor does it provide the current local time of the location
            # so first figure out the current time from the hourly forecasts. the first item is always 'now', which isn't helpful so skip it
            if len(data['forecasts'][0]['conditionsForecasts']) > 1: # make sure there's at least two items left in the hourly forecast for today
                for item in data['forecasts'][0]['conditionsForecasts']:
                    if item['time'] == 'Now' or item['text'] == 'Sunrise' or item['text'] == 'Sunset':
                        continue
                    approxtime  = item['time'] # time of the 'next' hour
                    if approxtime == 'Midnight':
                        approxtime = '12 AM'
                    elif approxtime == 'Noon':
                        approxtime = '12 PM'
                    break
            else:
                for item in data['forecasts'][1]['conditionsForecasts']: # at +/- 11PM we have only 'now' in the hourly forecast, so look at the next day
                    if item['text'] == 'Sunrise' or item['text'] == 'Sunset':
                        continue
                    approxtime  = item['time'] # time of the 'next' hour
                    if approxtime == 'Midnight':
                        approxtime = '12 AM'
                    elif approxtime == 'Noon':
                        approxtime = '12 PM'
                    break
            approxhour = time.strptime(approxtime, '%I %p')
            currenthour = approxhour.tm_hour - 1 # substract 1 hour to get the 'current' hour
            # let's define day and night based on sunrise and sunset
            sunrise = time.strptime(data['location']['sunrise'], '%I:%M %p')
            sunset = time.strptime(data['location']['sunset'], '%I:%M %p')
            sunrisehour = sunrise.tm_hour
            sunsethour = sunset.tm_hour
            if currenthour < sunrisehour or currenthour >= sunsethour: # current hour is after sunset and before sunrise: it's night
                condition = '%s Night' % data['location']['outlook']
            else:
                condition = '%s Day' % data['location']['outlook'] # current hour is between sunrise and sunset; it's day
        else:
            condition = data['location']['outlook']
        set_property('Current.OutlookIcon'         , '%s.png' % OUTLOOK[condition]) # Kodi translates it to Current.ConditionIcon
        set_property('Current.FanartCode'          , OUTLOOK[condition])
        set_property('Current.Wind'                , convert_speed(data['forecasts'][0]['windForecasts'][0]['speed'], 'mph', 'kmh'))
        set_property('Current.WindDirection'       , xbmc.getLocalizedString(WINDDIR[data['forecasts'][0]['windForecasts'][0]['direction']]))
        set_property('Current.Humidity'            , data['conditions']['condition']['value'].rstrip('%'))
        set_property('Current.DewPoint'            , convert_temp(data['conditions']['condition']['text'].split('.')[0].lstrip('The dew point is ').rstrip('°F'), 'F', 'C'))
        set_property('Current.FeelsLike'           , convert_temp(data['location']['realfeel'], 'F', 'C'))
    #current - extended
        set_property('Current.WindChill'           , convert_temp(windchill(data['location']['temperature'], data['forecasts'][0]['windForecasts'][0]['speed']), 'F') + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Current.Visibility'      , data['conditions']['conditions']['visibility']['value'] + ' mi')
            set_property('Current.Pressure'        , str(round(float(data['conditions']['conditions']['barometricPressure']['value']),2)) + ' inHg')
        else:
            set_property('Current.Visibility'      , str(round(1.60934 * int(data['conditions']['conditions']['visibility']['value']))) + ' km')
            set_property('Current.Pressure'        , str(int(round((33.864 * float(data['conditions']['conditions']['barometricPressure']['value']))))) + ' mbar')
        set_property('Current.Precipitation'       , str(data['forecasts'][0]['precipitationForecasts'][0]['probabilityOfPrecipitation']) + '%')
        if 'F' in TEMPUNIT:
            set_property('Current.PrecipitationAmount' , str(data['forecasts'][0]['precipitationForecasts'][0]['absoluteQuantity']) + 'in')
        else:
            set_property('Current.PrecipitationAmount' , str(round(data['forecasts'][0]['precipitationForecasts'][0]['absoluteQuantity'] * 25.4)) + 'mm')
        set_property('Current.IsFetched'           , 'true')
    #forecast - extended
        set_property('Forecast.City'               , data['location']['town'])
        set_property('Forecast.Country'            , data['location']['country'])
        set_property('Forecast.IsFetched'          , 'true')
    #today - extended
        set_property('Today.Sunrise'               , convert_datetime(data['location']['sunrise'], 'ampm', None, None))
        set_property('Today.Sunset'                , convert_datetime(data['location']['sunset'], 'ampm', None, None))


        # RNSE: Sonnenaufgang / Sonnenuntergang als Sonderkarte
        #
        # Nur anzeigen, wenn das naechste Ereignis maximal
        # ca. 3 Stunden entfernt ist.
        set_property('Today.SunEvent.Visible', '')
        set_property('Today.SunEvent.Type', '')
        set_property('Today.SunEvent.Label', '')
        set_property('Today.SunEvent.Time', '')
        set_property('Today.SunEvent.Slot', '')
        set_property('Today.SunEvent.Icon', '')

        try:
            # Yahoo liefert keine direkte aktuelle Ortszeit.
            # Deshalb nehmen wir den ersten echten Hourly-Eintrag
            # und ziehen eine Stunde ab.
            next_hour = None

            for sun_item in data['forecasts'][0]['conditionsForecasts']:
                if (
                    sun_item['time'] == 'Now'
                    or sun_item['text'] == 'Sunrise'
                    or sun_item['text'] == 'Sunset'
                ):
                    continue

                next_hour = sun_item['time']
                break

            # Spaet nachts kann heute nur noch "Now" vorhanden sein.
            if not next_hour:
                for sun_item in data['forecasts'][1]['conditionsForecasts']:
                    if sun_item['text'] in ['Sunrise', 'Sunset']:
                        continue

                    next_hour = sun_item['time']
                    break

            if next_hour:

                if next_hour == 'Midnight':
                    next_hour = '12 AM'
                elif next_hour == 'Noon':
                    next_hour = '12 PM'

                parsed_next = time.strptime(next_hour, '%I %p')

                current_minutes = (
                    parsed_next.tm_hour * 60
                    - 60
                ) % 1440

                def parse_sun_minutes(value):
                    parsed = time.strptime(value, '%I:%M %p')
                    return parsed.tm_hour * 60 + parsed.tm_min

                sunrise_minutes = parse_sun_minutes(
                    data['location']['sunrise']
                )

                sunset_minutes = parse_sun_minutes(
                    data['location']['sunset']
                )

                candidates = []

                for event_type, event_minutes in [
                    ('Sunrise', sunrise_minutes),
                    ('Sunset', sunset_minutes)
                ]:
                    delta = (
                        event_minutes - current_minutes
                    ) % 1440

                    if 0 < delta <= 180:
                        candidates.append(
                            (
                                delta,
                                event_type
                            )
                        )

                if candidates:
                    candidates.sort()
                    delta, event_type = candidates[0]

                    if delta <= 60:
                        slot = 2
                    elif delta <= 120:
                        slot = 3
                    else:
                        slot = 4

                    if event_type == 'Sunrise':
                        label = '↑ Sonne'
                        event_time = convert_datetime(
                            data['location']['sunrise'],
                            'ampm',
                            None,
                            None
                        )

                        # Platzhalter: Sonne
                        icon = '32.png'

                    else:
                        label = '↓ Sonne'
                        event_time = convert_datetime(
                            data['location']['sunset'],
                            'ampm',
                            None,
                            None
                        )

                        # Platzhalter: Mond
                        icon = '31.png'

                    set_property(
                        'Today.SunEvent.Visible',
                        'true'
                    )

                    set_property(
                        'Today.SunEvent.Type',
                        event_type
                    )

                    set_property(
                        'Today.SunEvent.Label',
                        label
                    )

                    set_property(
                        'Today.SunEvent.Time',
                        event_time
                    )

                    set_property(
                        'Today.SunEvent.Slot',
                        str(slot)
                    )

                    set_property(
                        'Today.SunEvent.Icon',
                        icon
                    )

                    log(
                        'RNSE SunEvent: '
                        + label
                        + ' '
                        + event_time
                        + ' slot '
                        + str(slot)
                    )

        except Exception as e:
            log(
                'RNSE SunEvent Fehler: '
                + str(e)
            )
        set_property('Today.Moonphase'             , MOONPHASE[data['conditions']['conditions']['moon']['title'].lower()])
        set_property('Today.MoonphaseIcon'         , data['conditions']['conditions']['moon']['icon'])
        set_property('Today.IsFetched'             , 'true')
    #hourly - extended
        #
        # Yahoo kann zwischen den normalen Stunden Einträge wie
        # "Sunrise" und "Sunset" liefern.
        #
        # Die ursprüngliche Version hat diese zwar übersprungen,
        # aber trotzdem den ursprünglichen Listenindex verwendet.
        # Dadurch entstanden Lücken wie:
        #
        # Hourly.1 = 20:00
        # Hourly.2 = leer
        # Hourly.3 = 21:00
        #
        # Deshalb nummerieren wir die tatsächlich verwendeten
        # Stunden hier selbst lückenlos von 1 bis 24.

        hourly_index = 1

        # Optionales Sonnenereignis für unsere OEM-Wetteransicht.
        #
        # Yahoo liefert Sunrise/Sunset direkt zwischen den normalen
        # Stundenwerten. Wir lassen die Hourly-Liste trotzdem
        # lückenlos und merken uns stattdessen die chronologische
        # Position des nächsten Sonnenereignisses separat.
        set_property('Today.SunEvent.Type', '')
        set_property('Today.SunEvent.Time', '')
        set_property('Today.SunEvent.Position', '')

        sun_event_found = False

        for day_index in range(2):

            conditions = data['forecasts'][day_index]['conditionsForecasts']
            precipitation = data['forecasts'][day_index]['precipitationForecasts']
            wind = data['forecasts'][day_index]['windForecasts']

            for source_index, item in enumerate(conditions):

                if item['text'] in ['Sunrise', 'Sunset']:
                    # Nur das nächste Ereignis des heutigen Tages
                    # interessiert die kompakte Hourly-Anzeige.
                    if day_index == 0 and not sun_event_found:
                        set_property(
                            'Today.SunEvent.Type',
                            item['text']
                        )
                        set_property(
                            'Today.SunEvent.Time',
                            convert_datetime(
                                item['time'],
                                'ampm',
                                None,
                                None
                            )
                        )
                        set_property(
                            'Today.SunEvent.Position',
                            str(hourly_index)
                        )
                        sun_event_found = True

                        log(
                            "RNSE SunEvent: "
                            + item['text']
                            + " at "
                            + convert_datetime(
                                item['time'],
                                'ampm',
                                None,
                                None
                            )
                            + " position "
                            + str(hourly_index)
                        )

                    continue

                if hourly_index > 24:
                    break

                set_property(
                    'Hourly.%i.Time' % hourly_index,
                    convert_datetime(
                        item['time'],
                        'ampm',
                        None,
                        None
                    )
                )

                if day_index == 0:
                    short_date = xbmc.getLocalizedString(33006)
                else:
                    short_date = xbmc.getLocalizedString(33007)

                set_property(
                    'Hourly.%i.ShortDate' % hourly_index,
                    short_date
                )

                set_property(
                    'Hourly.%i.Temperature' % hourly_index,
                    convert_temp(
                        item['temperature'],
                        'F'
                    ) + TEMPUNIT
                )

                set_property(
                    'Hourly.%i.Outlook' % hourly_index,
                    CONDITION.get(
                        item['iconLabel'],
                        item['iconLabel']
                    )
                )

                if item['iconLabel'] in [
                    'Mostly Cloudy',
                    'Partly Cloudy',
                    'Fair'
                ]:
                    if 'Night' in item['icon']:
                        condition = '%s Night' % item['iconLabel']
                    else:
                        condition = '%s Day' % item['iconLabel']
                else:
                    condition = item['iconLabel']

                set_property(
                    'Hourly.%i.OutlookIcon' % hourly_index,
                    '%s.png' % OUTLOOK[condition]
                )

                set_property(
                    'Hourly.%i.FanartCode' % hourly_index,
                    OUTLOOK[condition]
                )

                # Niederschlag derselben Yahoo-Stunde
                if source_index < len(precipitation):
                    precip = precipitation[source_index]

                    if 'F' in TEMPUNIT:
                        amount = (
                            str(precip['absoluteQuantity'])
                            + 'in'
                        )
                    else:
                        amount = (
                            str(
                                round(
                                    precip['absoluteQuantity']
                                    * 25.4
                                )
                            )
                            + 'mm'
                        )

                    set_property(
                        'Hourly.%i.PrecipitationAmount'
                        % hourly_index,
                        amount
                    )

                    set_property(
                        'Hourly.%i.Precipitation'
                        % hourly_index,
                        str(
                            precip[
                                'probabilityOfPrecipitation'
                            ]
                        ) + '%'
                    )

                # Wind derselben Yahoo-Stunde
                if source_index < len(wind):
                    wind_item = wind[source_index]

                    set_property(
                        'Hourly.%i.WindDirection'
                        % hourly_index,
                        xbmc.getLocalizedString(
                            WINDDIR[
                                wind_item['direction']
                            ]
                        )
                    )

                    set_property(
                        'Hourly.%i.WindSpeed'
                        % hourly_index,
                        convert_speed(
                            wind_item['speed'],
                            'mph'
                        ) + SPEEDUNIT
                    )

                hourly_index += 1

            if hourly_index > 24:
                break

        set_property('Hourly.IsFetched'          , 'true')

    def get_daily_weather(data):
    #daily - standard
        for count, item in enumerate(data['forecasts']):
            try:
                day, date = item['date'].split(' ')
                set_property('Day%i.Title'       % count, xbmc.getLocalizedString(LONGDAY[day]) + ' ' + date)
            except:
                day = item['date']
                set_property('Day%i.Title'       % count, xbmc.getLocalizedString(LONGDAY[day]))
            set_property('Day%i.HighTemp'        % count, convert_temp(item['highTemperature'], 'F', 'C'))
            set_property('Day%i.LowTemp'         % count, convert_temp(item['lowTemperature'], 'F', 'C'))
            set_property('Day%i.Outlook'         % count, item['iconLabel'])
            if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                condition = '%s Day' % item['iconLabel']
            else:
                condition = item['iconLabel']
            set_property('Day%i.OutlookIcon'      % count, '%s.png' % OUTLOOK[condition])
            set_property('Day%i.FanartCode'       % count, OUTLOOK[condition])
            if count == MAXDAYS:
                break
    #daily - extended
        for count, item in enumerate(data['forecasts']):
            try:
                day, date = item['date'].split(' ')
                set_property('Daily.%i.ShortDay'     % (count + 1), xbmc.getLocalizedString(SHORTDAY[day]))
                set_property('Daily.%i.LongDay'      % (count + 1), xbmc.getLocalizedString(LONGDAY[day]))
                set_property('Daily.%i.ShortDate'    % (count + 1), date)
                set_property('Daily.%i.LongDate'     % (count + 1), date)
            except:
                day = item['date']
                set_property('Daily.%i.ShortDay'     % (count + 1), xbmc.getLocalizedString(SHORTDAY[day]))
                set_property('Daily.%i.LongDay'      % (count + 1), xbmc.getLocalizedString(LONGDAY[day]))
                set_property('Daily.%i.ShortDate'    % (count + 1), '')
                set_property('Daily.%i.LongDate'     % (count + 1), '')
            set_property('Daily.%i.HighTemperature'  % (count + 1), convert_temp(item['highTemperature'], 'F') + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count + 1), convert_temp(item['lowTemperature'], 'F') + TEMPUNIT)
            set_property('Daily.%i.Outlook'          % (count + 1), CONDITION.get(item['iconLabel'], item['iconLabel']))

            if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                condition = '%s Day' % item['iconLabel']
            else:
                condition = item['iconLabel']
            set_property('Daily.%i.OutlookIcon'      % (count + 1), '%s.png' % OUTLOOK[condition])
            set_property('Daily.%i.FanartCode'       % (count + 1), OUTLOOK[condition])
        set_property('Daily.IsFetched'               , 'true')
