d=$1
DT=$2

while [ "$d" != "$DT" ]
do
    O_FILE=${d}_lonlat_datetime.csv
    python3 ../get_AltAz_datetime.py -d $d >> $O_FILE
    d=$(TZ=UTC date "+%Y%m%d" -d "$d + 1 day")
done