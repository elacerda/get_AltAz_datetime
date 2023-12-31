import sys
import glob
import numpy as np
import argparse as ap
from os import getenv
import astropy.units as u
from zoneinfo import ZoneInfo
from astropy.time import Time
from astroplan import Observer
from os.path import basename, join, isfile, isdir
from astropy.io.fits import getheader
from datetime import datetime, timezone
from astropy.coordinates import EarthLocation, Angle, SkyCoord

###
### CONSTANTS
###
__script_name__ = basename(sys.argv[0])
__script_telegram_desc__ = 'Check FITS header ALT, AZ DATETIME difference from DATE-OBS DATETIME.'
__telegram_commands__ = """
List of Commands:

    /getAltDTDir YYYYMMDD [0/1 to PLOT]
        Get datetime from Altitude fit for all files *.fits.fz from /IMAGE_PATH/YYYYMMDD/
    /getAzDTDir YYYYMMDD [0/1 to PLOT]
        Get datetime from Azimuth fit for all files *.fits.fz from /IMAGE_PATH/YYYYMMDD/
    /getAltDTFile FILENAME [0/1 to PLOT]
        Get datetime from Altitude fit for file FILENAME
    /getAzDTFile FILENAME [0/1 to PLOT]
        Get datetime from Azimuth fit for file FILENAME
    /getAltAzDTFile FILENAME GET_FROM_AZ=0/1 PLOT=0/1 TIME_RANGE=-X,X  HEADERCARD
        Complete function to handle fit.
    /listImages YYYYMMDD
        List all files from directory /IMAGE_PATH/YYYYMMDD/
"""
__script_desc__ = """
Check FITS header ALT, AZ DATETIME difference from DATE-OBS DATETIME.
Uses the RA, DEC and DATE-OBS to create a timeline to retrieve the 
closer timestamp from the event (object passing the registered altitude).
Can also retrieve the timestamp from the azimuth fit using --get_from_az 
option.
"""
# Bot Telegram https://t.me/t80s_altaz_dt_bot
TELEGRAM_BOT_API_KEY = getenv('TELEGRAM_ALTAZ_BOT_API_KEY')
# T80S Reduction PATH
IMAGES_PATH = getenv('IMGPATH')
# TIMEZONES
T80S_TZ_STR = 'America/Santiago'
T80S_TZ = ZoneInfo(T80S_TZ_STR)
UTC_TZ = timezone.utc

def parse_arguments():
    parser = ap.ArgumentParser(prog=__script_name__, description=__script_desc__)
    parser.add_argument('--filename', '-f', 
                        metavar='FITSFILE', default=None, type=str, 
                        help='Observed Image FITS filename.')
    parser.add_argument('--telegram', '-t', 
                        action='store_true', default=False, 
                        help='Start script as a Telegram Bot SERVICE (other arguments will be ignored).')
    parser.add_argument('--header_date', '-D', 
                        metavar='HEADERCARD', default='DATE-OBS', type=str, 
                        help='FITS header card used to get datetime. Defaults to DATE-OBS.')
    parser.add_argument('--date', '-d', 
                        metavar='YYYYMMDD', default=None, type=str, 
                        help='Check all files from the same YYYYMMDD directory. If --filename is passed, --date will be ignored.')
    parser.add_argument('--plot', '-p', 
                        action='store_true', default=False, 
                        help='Plot the ALT/AZ datetime fit.')
    parser.add_argument('--get_from_az', 
                        action='store_true', default=False, 
                        help='Get datetime from Azimuth fit instead from the Altitude (UNSTABLE).')  
    time_range_help = 'Creates the timeline centred in header card used to retrieve the datetime. '
    time_range_help += 'Example: -T -100 100 will create a timeline of 200 seconds centered in header '
    time_range_help += 'card used to retrieve the datetime. Defaults to -100 100.'
    parser.add_argument('--time_range', '-T', metavar='SECONDS', type=int, nargs=2, default=[-100, 100],
                        help=time_range_help)
    args = parser.parse_args(args=sys.argv[1:])

    # Parse arguments
    if args.filename is not None:
        if not isfile(args.filename):
            raise FileNotFoundError(f'{__script_name__}: {args.filename}: file not exists')
        if 'bias' in args.filename:            
            raise NotImplementedError(f'{__script_name__}: {args.filename}: bias file')
        if 'skyflat' in args.filename:            
            raise NotImplementedError(f'{__script_name__}: {args.filename}: skyflat file')
    if args.date is not None:
        if len(args.date) != 8:
            print(f'Usage: {__script_name__} YYYYMMDD')
            sys.exit(1)
        args.imgdir = join(IMAGES_PATH, f'{args.date}')
        if not isdir(args.imgdir):
            print(f'{__script_name__}: {args.imgdir}: directory does not exists')
            sys.exit(1)
        args.imgwildcard = join(args.imgdir, '*.fits.fz')
        args.imgglob = glob.glob(args.imgwildcard)
        nfiles = len(args.imgglob)
        if nfiles == 0:
            print(f'{__script_name__}: {args.imgwildcard}: files not found')
            sys.exit(1)
    return args

def get_altaz_dt_new(filename, dt_card=None):
    """
    TODO: Need HELP! 
    """
    import pytz

    # HEADER
    hdr = getheader(filename, 1)

    # LOCATION
    T80S_LAT = hdr.get('HIERARCH T80S TEL GEOLAT')  #'-30.1678638889 degrees'
    T80S_LON = hdr.get('HIERARCH T80S TEL GEOLON')  #'-70.8056888889 degrees'
    T80S_HEI = eval(hdr.get('HIERARCH T80S TEL GEOELEV'))  #2187
    t80s_lat = Angle(T80S_LAT, 'deg')
    t80s_lon = Angle(T80S_LON, 'deg')
    t80s_hei = T80S_HEI*u.m
    t80s_EL = EarthLocation(lat=t80s_lat, lon=t80s_lon, height=t80s_hei)
    t80s_tz = pytz.timezone(T80S_TZ_STR)

    t80s_obs = Observer(location=t80s_EL, timezone=t80s_tz)

    # DATETIME
    if dt_card is None:
        dt_card = 'DATE-OBS'
    dt_obs = pytz.utc.localize(datetime.fromisoformat(hdr.get(dt_card)))
    t80s_Time = t80s_obs.datetime_to_astropy_time(dt_obs)

    # TARGET
    target_coords = SkyCoord(ra=hdr.get('CRVAL1'), dec=hdr.get('CRVAL2'), unit=(u.deg, u.deg))
    try:
        _alt = hdr.get('ALT', None)
    except:
        _alt = hdr.get('HIERARCH T80S TEL EL START', None)
    if _alt is None:
        return f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},None,None'
    
    target_input_alt = Angle(_alt, 'deg')

    _times = []
    _difftimes = []
    for _T in [t80s_Time-10*u.min, t80s_Time, t80s_Time+10*u.min]:
        rtime = t80s_obs.target_rise_time(
            _T,
            target_coords,
            horizon=target_input_alt,
            which='nearest',
            n_grid_points=1800,
        )
        _times.append(rtime)
        _difftimes.append((rtime - t80s_Time).sec)
        stime = t80s_obs.target_set_time(
            _T,
            target_coords,
            horizon=target_input_alt,
            which='nearest',
            n_grid_points=1800,
        )
        _times.append(stime)
        _difftimes.append((stime - t80s_Time).sec)
    i_min = np.argmin(np.abs(_difftimes)) 
    target_dt_utc = _times[i_min].datetime
    diff_time = _difftimes[i_min]
    final_message = f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},{target_dt_utc},{diff_time}'

    return final_message

def get_altaz_dt(filename, get_from_az=False, plot=False, time_range=[-100, 1000], dt_card=None, debug=False):
    """
    TODO: Need HELP! 
    """
    # HEADER
    hdr = getheader(filename, 1)

    # LOCATION
    T80S_LAT = hdr.get('HIERARCH T80S TEL GEOLAT')  #'-30.1678638889 degrees'
    T80S_LON = hdr.get('HIERARCH T80S TEL GEOLON')  #'-70.8056888889 degrees'
    T80S_HEI = eval(hdr.get('HIERARCH T80S TEL GEOELEV'))  #2187
    t80s_lat = Angle(T80S_LAT, 'deg')
    t80s_lon = Angle(T80S_LON, 'deg')
    t80s_hei = T80S_HEI*u.m
    t80s_EL = EarthLocation(lat=t80s_lat, lon=t80s_lon, height=t80s_hei)

    # DATETIME
    if dt_card is None:
        dt_card = 'DATE-OBS'
    str_dt_obs = hdr.get(dt_card) + '+00:00'
    dt_obs = datetime.fromisoformat(str_dt_obs)
    t80s_dt = dt_obs.astimezone(T80S_TZ)
    t80s_Time = Time(t80s_dt, location=t80s_EL)

    # TIMELINE
    tmin, tmax = time_range
    time_n = (tmax - tmin) + 1
    timeline = t80s_Time + u.second*np.linspace(tmin, tmax, time_n)
    timeline_lin = np.asarray(list(range(time_n)))

    # OBSERVER
    t80s_obs = Observer(location=t80s_EL, timezone=T80S_TZ)

    # TARGET
    target_coords = SkyCoord(ra=hdr.get('CRVAL1'), dec=hdr.get('CRVAL2'), unit=(u.deg, u.deg))
    target_AltAz = t80s_obs.altaz(timeline, target=target_coords)
    target_dt_utc = None

    # TARGET ALT
    _alt = hdr.get('HIERARCH T80S TEL EL START', None)
    if _alt is not None:
        target_in_alt = Angle(_alt, 'deg')
        #target_in_alt = Angle(hdr.get('ALT'), 'deg')
        p_alt = np.polyfit(target_AltAz.alt.value, timeline_lin, 2)
        i_alt = int(np.polyval(p_alt, target_in_alt.value))
        target_alt_Time = timeline[i_alt]
        target_alt_dt_utc = target_alt_Time.to_datetime().replace(tzinfo=UTC_TZ)
        target_dt_utc = target_alt_dt_utc

    # TARGET AZ
    _az = hdr.get('HIERARCH T80S TEL AZ START', None)
    if _az is not None:
        target_in_az = Angle(_az, 'deg')
        #target_in_az = Angle(hdr.get('AZ'), 'deg')
        p_az = np.polyfit(target_AltAz.az.value, timeline_lin, 2)
        i_az = int(np.polyval(p_az, target_in_az.value))
        target_az_Time = timeline[i_az]
        target_az_dt_utc = target_az_Time.to_datetime().replace(tzinfo=UTC_TZ)
        target_dt_utc = target_az_dt_utc

    if target_dt_utc is not None:
        if get_from_az:
            diff_time_az = (target_az_dt_utc - dt_obs).total_seconds()
            diff_time = diff_time_az
        else:
            diff_time_alt = (target_alt_dt_utc - dt_obs).total_seconds()
            diff_time = diff_time_alt

        # FINAL PRINT
        final_message = f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},{target_dt_utc},{diff_time}'
    else:
        final_message = f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},None,None'

    ##########################################################################################
    # DEBUG
    ##########################################################################################
    if debug:
        # PRINT 
        print(f'{diff_time_alt=} {diff_time_az=}')

        # ASSERT ALT
        target_alt_dt_t80s = target_alt_dt_utc.astimezone(T80S_TZ)
        _tmp = (target_alt_dt_t80s - t80s_dt).total_seconds()
        assert(diff_time_alt == _tmp)

        # ASSERT AZ
        target_az_dt_t80s = target_az_dt_utc.astimezone(T80S_TZ)
        _tmp = (target_az_dt_t80s - t80s_dt).total_seconds()
        assert(diff_time_az == _tmp)    
    ##########################################################################################
    
    ##########################################################################################
    # PLOT
    ##########################################################################################
    if (target_dt_utc is not None) & plot:
        from matplotlib import pyplot as plt
        from matplotlib.dates import DateFormatter

        f, (axalt, axaz) = plt.subplots(1, 2)
        axalt.plot(timeline.value, target_AltAz.alt)
        x_timeline = np.polyval(p_alt, target_AltAz.alt.value)
        i_timeline = x_timeline.astype(int)
        i_timeline = i_timeline[(i_timeline > 0) & (i_timeline < time_n)]
        axalt.plot(timeline.value[i_timeline], target_AltAz.alt.value[i_timeline], c='orange', ls='-.')
        axalt.axhline(y=target_in_alt.value, ls='--', c='k', label=f'{target_in_alt.value}')
        axalt.axvline(x=timeline.value[i_alt], ls='--', c='b', label=f'{timeline.value[i_alt]}')
        axalt.set_ylabel('Altitude [deg]')
        axaz.plot(timeline.value, target_AltAz.az)
        x_timeline = np.polyval(p_az, target_AltAz.az.value)
        i_timeline = x_timeline.astype(int)
        i_timeline = i_timeline[(i_timeline > 0) & (i_timeline < time_n)]
        axaz.plot(timeline.value[i_timeline], target_AltAz.az.value[i_timeline], c='orange', ls='-.')
        axaz.axhline(y=target_in_az.value, ls='--', c='k', label=f'{target_in_az.value}')
        axaz.axvline(x=timeline.value[i_az], ls='--', c='b', label=f'{timeline.value[i_az]}')
        axaz.set_ylabel('Azimuth [deg]')
        for ax in (axalt, axaz):
            formatter = DateFormatter('%H:%M:%S', tz=T80S_TZ)
            ax.xaxis.set_major_formatter(formatter)
            plt.setp(ax.get_xticklabels(), rotation=45)      
            ax.set_xlabel('Time')
            ax.legend(frameon=False, loc=1)
            ax.grid()
        f.set_size_inches(10, 5)
        f.suptitle(hdr.get('TIME'))
        f.tight_layout()
        image_filename = 'target_alt_az.png'
        f.savefig(image_filename)
        plt.close(f)
    else:
        image_filename = None
    ##########################################################################################

    return final_message, image_filename

def main_telegram_v13():
    from telegram import Update
    from telegram.ext import Updater, CallbackContext, CommandHandler

    def start(update: Update, context: CallbackContext):
        _msg = __script_telegram_desc__ + __telegram_commands__
        update.message.reply_text(_msg)

    def list_images(update: Update, context: CallbackContext):
        ok = False
        try:
            input_YYYYMMDD = context.args[0]
            ok = True
        except:
            update.message.reply_text('USAGE: /listImages YYYYMMDD')
        if ok:
            _wildcard = join(IMAGES_PATH, f'{input_YYYYMMDD}', '*.fits.fz')
            _iter = glob.glob(_wildcard)
            if len(_iter) > 0:
                for file in _iter:
                    update.message.reply_text(file)
            else:
                update.message.reply_text(f'{_wildcard}: no files found')

    def get_alt_dt_dir(update: Update, context: CallbackContext):
        ok = False
        try:
            input_YYYYMMDD = context.args[0]
            ok = True
        except:
            update.message.reply_text('USAGE: /getAltDTDir YYYYMMDD [0/1 PLOT]')
        if ok:
            try:
                plot = bool(eval(context.args[1]))
            except:
                plot = False

            if plot:
                update.message.reply_text('PLOT ON')
            else:
                update.message.reply_text('PLOT OFF')
            _wildcard = join(IMAGES_PATH, f'{input_YYYYMMDD}', '*.fits.fz')
            _iter = glob.glob(_wildcard)
            if len(_iter) > 0:
                for file in _iter:
                    _msg, image_path = get_altaz_dt(file, get_from_az=False, plot=plot)
                    if image_path is not None:
                        photo_file_id = open(image_path, 'rb')
                        context.bot.send_photo(
                            chat_id=update.message['chat']['id'],
                            photo=photo_file_id,
                            filename=image_path
                        )
                    update.message.reply_text(_msg)
            else:
                update.message.reply_text(f'{_wildcard}: no files found')


    def get_alt_dt_file(update: Update, context: CallbackContext):
        ok = False
        try:
            file = context.args[0]
            ok = True
        except:
            update.message.reply_text('USAGE: /getAltDTFile FILENAME [0/1 PLOT]')
        if ok:
            try:
                plot = bool(eval(context.args[1]))
            except:
                plot = False
            if plot:
                update.message.reply_text('PLOT ON')
            else:
                update.message.reply_text('PLOT OFF')
            _msg, image_path = get_altaz_dt(file, get_from_az=False, plot=plot)
            if image_path is not None:
                photo_file_id = open(image_path, 'rb')
                context.bot.send_photo(
                    chat_id=update.message['chat']['id'],
                    photo=photo_file_id,
                    filename=image_path
                )
            update.message.reply_text(_msg)

    def get_az_dt_dir(update: Update, context: CallbackContext):
        ok = False
        try:
            input_YYYYMMDD = context.args[0]
            ok = True
        except:
            update.message.reply_text('USAGE: /getAzDTDir YYYYMMDD [0/1 PLOT]')
        try:
            plot = bool(eval(context.args[1]))
        except:
            plot = False

        if plot:
            update.message.reply_text('PLOT ON')
        else:
            update.message.reply_text('PLOT OFF')
            _wildcard = join(IMAGES_PATH, f'{input_YYYYMMDD}', '*.fits.fz')
            _iter = glob.glob(_wildcard)
            if len(_iter) > 0:
                for file in _iter:
                    _msg, image_path = get_altaz_dt(file, get_from_az=True, plot=plot)
                    if image_path is not None:
                        photo_file_id = open(image_path, 'rb')
                        context.bot.send_photo(
                            chat_id=update.message['chat']['id'],
                            photo=photo_file_id,
                            filename=image_path
                        )
                    update.message.reply_text(_msg)
            else:
                update.message.reply_text(f'{_wildcard}: no files found')

    def get_az_dt_file(update: Update, context: CallbackContext):
        ok = False
        try:
            file = context.args[0]
            ok = True
        except:
            update.message.reply_text('USAGE: /getAzDTFile FILENAME [0/1 PLOT]')
        if ok:
            try:
                plot = bool(eval(context.args[1]))
            except:
                plot = False
            if plot:
                update.message.reply_text('PLOT ON')
            else:
                update.message.reply_text('PLOT OFF')
            _msg, image_path = get_altaz_dt(file, get_from_az=True, plot=plot)
            if image_path is not None:
                photo_file_id = open(image_path, 'rb')
                context.bot.send_photo(
                    chat_id=update.message['chat']['id'],
                    photo=photo_file_id,
                    filename=image_path
                )
            update.message.reply_text(_msg)

    def get_altaz_dt_file(update: Update, context: CallbackContext):
        ok = False
        try:
            filename, get_from_az, plot, time_range, dt_card = context.args
            ok = True
        except:
            update.message.reply_text('USAGE: /getAltAzDTFile FILENAME GET_FROM_AZ PLOT TIME_RANGE HEADERCARD')    
        if ok:
            get_from_az = bool(eval(get_from_az))
            plot = bool(eval(plot))
            time_range = list(eval(time_range))
            if plot:
                update.message.reply_text('PLOT ON')
            else:
                update.message.reply_text('PLOT OFF')
            _msg, image_path = get_altaz_dt(
                filename, 
                get_from_az=get_from_az, 
                time_range=time_range,
                plot=plot,
                dt_card=dt_card,
            )
            if image_path is not None:
                photo_file_id = open(image_path, 'rb')
                context.bot.send_photo(
                    chat_id=update.message['chat']['id'],
                    photo=photo_file_id,
                    filename=image_path
                )
            update.message.reply_text(_msg)

    updater = Updater(TELEGRAM_BOT_API_KEY)
    
    dispatcher = updater.dispatcher

    # Commands
    get_alt_dt_dir_handler = CommandHandler('getAltDTDir', get_alt_dt_dir)
    dispatcher.add_handler(get_alt_dt_dir_handler)
    get_az_dt_dir_handler = CommandHandler('getAzDTDir', get_az_dt_dir)
    dispatcher.add_handler(get_az_dt_dir_handler)
    get_alt_dt_file_handler = CommandHandler('getAltDTFile', get_alt_dt_file)
    dispatcher.add_handler(get_alt_dt_file_handler)
    get_az_dt_file_handler = CommandHandler('getAzDTFile', get_az_dt_file)
    dispatcher.add_handler(get_az_dt_file_handler)
    get_altaz_dt_file_handler = CommandHandler('getAltAzDTFile', get_altaz_dt_file)
    dispatcher.add_handler(get_altaz_dt_file_handler)
    list_images_handler = CommandHandler('listImages', list_images)
    dispatcher.add_handler(list_images_handler)
    
    # Start Command
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    updater.start_polling()
    updater.idle()

def main_date(args):
    for filename in args.imgglob:
        final_message = get_altaz_dt_new(
            filename=filename, 
            dt_card=args.header_date
        )
#        final_message, image_filename = get_altaz_dt(
#            filename=filename, 
#            get_from_az=args.get_from_az, 
#            time_range=args.time_range,
#            plot=args.plot,
#        )
        print(final_message)

if __name__ == '__main__':
    args = parse_arguments()

    if args.telegram:
        main_telegram_v13()
    else:
        if args.filename is not None:
            final_message = get_altaz_dt_new(
                filename=args.filename, 
                dt_card=args.header_date,
            )
#            final_message, image_filename = get_altaz_dt(
#                filename=args.filename, 
#                get_from_az=args.get_from_az, 
#                time_range=args.time_range,
#                plot=args.plot,
#                dt_card=args.header_date,
#            )
            print(final_message)
        elif args.date is not None:
            main_date(args)

"""
###
### python-telegram-bot v20
###
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=USAGE_MESSAGE)

async def get_alt_dt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _text = context.args
    input_YYYYMMDD = context.args[0]
    try:
        plot = bool(context.args[1])
    except:
        plot = False
    _wildcard = join(IMAGES_PATH, f'{input_YYYYMMDD}', '*.fits.fz')
    for file in glob.glob(_wildcard):
        _msg = get_altaz_dt(file, get_from_az=False, debug=False, plot=plot)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_msg)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    get_alt_dt_handler = CommandHandler('get_alt_dt', get_alt_dt)
    application.add_handler(get_alt_dt_handler)

    application.run_polling()
"""
