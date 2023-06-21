Get AltAz DATETIME
==================

Check FITS header ALT, AZ DATETIME difference from DATE-OBS DATETIME.
Uses the RA, DEC and DATE-OBS to create a timeline to retrieve the 
closer timestamp from the event (object passing the registered altitude).
Can also retrieve the timestamp from the azimuth fit using --get_from_az 
option.

Usage
-----

**Get AltAz DATETIME** usage:

	usage: get_AltAz_datetime.py [-h] [--filename FITSFILE] [--telegram] [--date YYYYMMDD]
				     [--plot] [--get_from_az] [--time_range FLOAT FLOAT]
				     [--time_bins N]

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
	  --time_range FLOAT FLOAT, -T FLOAT FLOAT
				Creates the timeline centred in header DATE-OBS. Example: -T
				-0.5,0.5 will create a timeline of 1 hour centered in header
				DATE-OBS.
	  --time_bins N         Number of timeline bins.

Contact
-------
	
Contact us: [dhubax@gmail.com](mailto:dhubax@gmail.com).
