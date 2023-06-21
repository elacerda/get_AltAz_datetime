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
    /getAltAzDTFile FILENAME GET_FROM_AZ=0/1 PLOT=0/1 TIME_RANGE=-X,X TIME_N=N
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
T80S_TZ = ZoneInfo('America/Santiago')
UTC_TZ = timezone.utc

def parse_arguments():
    parser = ap.ArgumentParser(prog=__script_name__, description=__script_desc__)
    parser.add_argument('--filename', '-f', 
                        metavar='FITSFILE', default=None, type=str, 
                        help='Observed Image FITS filename.')
    parser.add_argument('--telegram', '-t', 
                        action='store_true', default=False, 
                        help='Start script as a Telegram Bot SERVICE (other arguments will be ignored).')
    parser.add_argument('--date', '-d', 
                        metavar='YYYYMMDD', default=None, type=str, 
                        help='Check all files from the same YYYYMMDD directory. If --filename is passed, --date will be ignored.')
    parser.add_argument('--plot', '-p', 
                        action='store_true', default=False, 
                        help='Plot the ALT/AZ datetime fit.')
    parser.add_argument('--get_from_az', 
                        action='store_true', default=False, 
                        help='Get datetime from Azimuth fit instead from the Altitude (UNSTABLE).')  
    time_range_help = 'Creates the timeline centred in header DATE-OBS. '
    time_range_help += 'Example: -T -0.5,0.5 will create a timeline of 1 hour centered in header DATE-OBS.'
    parser.add_argument('--time_range', '-T', metavar='FLOAT', type=float, nargs=2, default=[-0.25, 0.25],
                        help=time_range_help)
    parser.add_argument('--time_bins', metavar='N', type=int, default=1800, 
                        help='Number of timeline bins.')
    args = parser.parse_args(args=sys.argv[1:])

    # Parse arguments
    if args.filename is not None:
        if not isfile(args.filename):
            print(f'{__script_name__}: {args.filename}: file not exists')
            sys.exit(1)
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

def get_altaz_dt(filename, get_from_az=False, plot=False, time_range=[-0.25, 0.25], time_n=1800, debug=False):
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
    str_dt_obs = hdr.get('DATE-OBS') + '+00:00'
    dt_obs = datetime.fromisoformat(str_dt_obs)
    t80s_dt = dt_obs.astimezone(T80S_TZ)
    t80s_Time = Time(t80s_dt, location=t80s_EL)

    # TIMELINE
    tmin, tmax = time_range
    timeline = t80s_Time + u.hour*np.linspace(tmin, tmax, time_n)
    timeline_lin = np.asarray(list(range(time_n)))

    # OBSERVER
    t80s_obs = Observer(location=t80s_EL, timezone=T80S_TZ)

    # TARGET
    target_coords = SkyCoord(ra=hdr.get('CRVAL1'), dec=hdr.get('CRVAL2'), unit=(u.deg, u.deg))
    target_AltAz = t80s_obs.altaz(timeline, target=target_coords)

    # TARGET ALT
    target_in_alt = Angle(hdr.get('HIERARCH T80S TEL EL START'), 'deg')
    #target_in_alt = Angle(hdr.get('ALT'), 'deg')
    p_alt = np.polyfit(target_AltAz.alt.value, timeline_lin, 3)
    i_alt = int(np.polyval(p_alt, target_in_alt.value))
    target_alt_Time = timeline[i_alt]
    target_alt_dt_utc = target_alt_Time.to_datetime().replace(tzinfo=UTC_TZ)
    target_dt_utc = target_alt_dt_utc

    # TARGET AZ
    target_in_az = Angle(hdr.get('HIERARCH T80S TEL AZ START'), 'deg')
    #target_in_az = Angle(hdr.get('AZ'), 'deg')
    p_az = np.polyfit(target_AltAz.az.value, timeline_lin, 3)
    i_az = int(np.polyval(p_az, target_in_az.value))
    target_az_Time = timeline[i_az]
    target_az_dt_utc = target_az_Time.to_datetime().replace(tzinfo=UTC_TZ)
    target_dt_utc = target_az_dt_utc

    if get_from_az:
        diff_time_az = (target_az_dt_utc - dt_obs).total_seconds()
        diff_time = diff_time_az
    else:
        diff_time_alt = (target_alt_dt_utc - dt_obs).total_seconds()
        diff_time = diff_time_alt

    # FINAL PRINT
    final_message = f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},{target_dt_utc},{diff_time}'

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
    if plot:
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
            filename, get_from_az, plot, time_range, time_n = context.args
            ok = True
        except:
            update.message.reply_text('USAGE: /getAltAzDTFile FILENAME GET_FROM_AZ PLOT TIME_RANGE TIME_N')    
        if ok:
            get_from_az = bool(eval(get_from_az))
            plot = bool(eval(plot))
            time_range = list(eval(time_range))
            time_n = int(time_n)
            if plot:
                update.message.reply_text('PLOT ON')
            else:
                update.message.reply_text('PLOT OFF')
            _msg, image_path = get_altaz_dt(
                filename, 
                get_from_az=get_from_az, 
                time_range=time_range,
                time_n=time_n,
                plot=plot,
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
        final_message, image_filename = get_altaz_dt(
            filename=filename, 
            get_from_az=args.get_from_az, 
            time_range=args.time_range,
            time_n=args.time_bins,
            plot=args.plot,
        )
        print(final_message)

if __name__ == '__main__':
    args = parse_arguments()

    if args.telegram:
        main_telegram_v13()
    else:
        if args.filename is not None:
            final_message, image_filename = get_altaz_dt(
                filename=args.filename, 
                get_from_az=args.get_from_az, 
                time_range=args.time_range,
                time_n=args.time_bins,
                plot=args.plot,
            )
            print(final_message)
        elif args.date is not None:
            main_date(args)

"""
#from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

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
