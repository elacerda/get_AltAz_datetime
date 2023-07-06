Get AltAz DATETIME
==================

Check FITS header ALT, AZ DATETIME difference from DATE-OBS DATETIME.
Uses the RA, DEC and DATE-OBS to create a timeline to retrieve the 
closer timestamp from the event (object passing the registered altitude).
Can also retrieve the timestamp from the azimuth fit using --get_from_az 
option.

The text output of the program is a csv row:

	FILENAME,OBJNAME,FILTER,DATETIME,DIFFTIME

	DATETIME is the timestamp found for the event (object at the Alt or Az)
	DIFFTIME is DATETIME - DATE-OBS

In order to check the fit, run the script with --plot command active in order to create
a nice plot showing the fit and the values for the altitude and azimuth.

Usage
-----

**Get AltAz DATETIME** usage:

	usage: get_AltAz_datetime.py [-h] [--filename FITSFILE] [--telegram] [--date YYYYMMDD]
				     [--plot] [--get_from_az] [--time_range FLOAT FLOAT]

	Check FITS header ALT, AZ DATETIME difference from DATE-OBS DATETIME. Uses the RA, DEC
	and DATE-OBS to create a timeline to retrieve the closer timestamp from the event (object
	passing the registered altitude). Can also retrieve the timestamp from the azimuth fit
	using --get_from_az option.

	options:
	  -h, --help            show this help message and exit
	  --filename FITSFILE, -f FITSFILE
				Observed Image FITS filename.
	  --telegram, -t        Start script as a Telegram Bot SERVICE (other arguments will be
				ignored).
	  --date YYYYMMDD, -d YYYYMMDD
				Check all files from the same YYYYMMDD directory. If --filename
				is passed, --date will be ignored.
	  --plot, -p            Plot the ALT/AZ datetime fit.
	  --get_from_az         Get datetime from Azimuth fit instead from the Altitude
				(UNSTABLE).
	  --time_range INT INT, -T INT INT
				Creates the timeline centred in header DATE-OBS. Example: -T
				-100 100 will create a timeline of 200 seconds centered in header
				DATE-OBS. Defaults to -100 100.

Telegram Bot
------------

This script also can start a telegram bot [T80S AltAz DATETIME](https://t.me/t80s_altaz_dt_bot).
It reads the enviroment variable TELEGRAM_ALTAZ_BOT_API_KEY. The bot has the following commands:

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

Contact
-------
	
Contact us: [dhubax@gmail.com](mailto:dhubax@gmail.com).
