DT=$1
O_FILE=${DT}_lonlat_datetime.csv

python3 ../get_AltAz_datetime.py -d $DT >> $O_FILE
