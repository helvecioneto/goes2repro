import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import sys
import os
import argparse
import tqdm
import pandas as pd
import s3fs
import pathlib
import xarray as xr
import rioxarray
import shutil
from pyproj import CRS
from goes2go import GOES
from concurrent.futures import ThreadPoolExecutor


def download(args):
    # Get bucket and time
    bucket, time = args
    # Set attempts
    attempt = 0
    while attempt < max_attempts:
        try:
            fs.get(bucket, bucket)
            # Create output path is output_path + year/month/day/
            output = f'{output_path}{time.strftime("%Y/%m/%d")}/'
            pathlib.Path(output).mkdir(parents=True, exist_ok=True)
            # Crop and reproject
            crop_reproject(bucket, output)
            return
        except:
            attempt += 1
    with open('fail.log', 'a') as log_file:
        log_file.write(f'Failed to download {bucket} at {time}\n')



def crop_reproject(file, output):
    # Open file
    ds = xr.open_dataset(file)
    # Select only var_name and goes_imager_projection
    ds = ds[[var_name, "goes_imager_projection"]]
    # Get projection
    sat_height = ds["goes_imager_projection"].attrs["perspective_point_height"]
    ds = ds.assign_coords({
                "x": ds["x"].values * sat_height,
                "y": ds["y"].values * sat_height,
            })
    # Set CRS
    crs = CRS.from_cf(ds["goes_imager_projection"].attrs)
    ds = ds.rio.write_crs(crs)

    # Reproject to EPSG:4326
    ds = ds.rio.reproject(dst_crs="EPSG:4326").rename({"x": "lon", "y": "lat"})

    # Crop using lat/lon coordinates
    ds = ds.rio.clip_box(minx=lon_min, miny=lat_min, maxx=lon_max, maxy=lat_max)

    # Remove any previous file
    if pathlib.Path(f'{output}{file.split("/")[-1]}.nc').exists():
        pathlib.Path(f'{output}{file.split("/")[-1]}.nc').unlink()

    # Add comments
    ds[var_name].attrs['comments'] = 'Cropped and reprojected to EPSG:4326 by helvecioblneto@gmail.com'

    # Save as netcdf
    ds.to_netcdf(f'{output}{file.split("/")[-1]}.nc')

    ds.close()

    # Remove original file using sys
    if pathlib.Path(file).exists():
        os.remove(file)

def main():

    global fs, output_path, var_name, lat_min, lat_max, lon_min, lon_max, max_attempts, parallel, latest, recent

    epilog = """
    Example usage:

    - To download and process data from the GOES-16 satellite for the ABI-L2-CMIPF product, andchannel 13

    goes2repro --satellite goes16 --product ABI-L2-CMIPF --var_name CMI --channel 13 --start_date "2022-12-15 00:00:00" --end_date "2022-12-15 01:00:00" --output_path "output/"
    
    
    - To download recent files from the GOES-16 satellite for the ABI-L2-CMIPF product, extracting the CMI variable from channel 13, in the last 30 minutes:

    goes2repro --satellite goes16 --product ABI-L2-CMIPF --var_name CMI --channel 13 --recent 30 --output_path "output/"
    """


    # Set arguments
    parser = argparse.ArgumentParser(description='Converts GOES-16 L2 data to netCDF',
                                    epilog=epilog,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)
    
    # Satellite and product settings
    parser.add_argument('--satellite', type=str, default='goes16', help='Name of the satellite (e.g., goes16)')
    parser.add_argument('--product', type=str, default='ABI-L2-CMIPF', help='Name of the satellite product')
    parser.add_argument('--var_name', type=str, default='CMI', help='Variable name to extract (e.g., CMI)')
    parser.add_argument('--channel', type=int, default=13, help='Channel to use (e.g., 13)')
    parser.add_argument('--domain', type=str, default='F', help='Domain to use (e.g., F or C)')

    # Date and time settings
    parser.add_argument('--start_date', type=str, default='2022-12-15 00:00:00', help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=str, default='2022-12-15 01:00:00', help='End date in YYYY-MM-DD format')
    parser.add_argument('--period', type=str, default='10 min', help='Frequency for the time range (e.g., "10 min")')
    parser.add_argument('--between_hours', nargs=2, type=int, default=[0, 23], help='Filter data between these hours (e.g., 0 23)')
    parser.add_argument('--between_minutes', nargs=2, type=int, default=[0, 60], help='Filter data between these minutes (e.g., 0 60)')

    # Output settings
    parser.add_argument('--output_path', type=str, default='output/', help='Path for saving output files')

    # Parallel processing
    parser.add_argument('--parallel', type=bool, default=True, help='Use parallel processing')
    parser.add_argument('--processes', type=int, default=4, help='Number of processes for parallel execution')

    # Geographic bounding box
    parser.add_argument('--lat_min', type=float, default=-56, help='Minimum latitude of the bounding box')
    parser.add_argument('--lat_max', type=float, default=35, help='Maximum latitude of the bounding box')
    parser.add_argument('--lon_min', type=float, default=-116, help='Minimum longitude of the bounding box')
    parser.add_argument('--lon_max', type=float, default=-25, help='Maximum longitude of the bounding box')

    # add recent 30 min
    parser.add_argument('--recent', type=int, default=0, help='Download the most recent files in the last X minutes')
    
    # Set max attempts
    parser.add_argument('--max_attempts', type=int, default=3, help='Number of attempts to download a file')

    # Parse arguments
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set output_path and var_name
    output_path = args.output_path
    var_name = args.var_name
    lat_min = args.lat_min
    lat_max = args.lat_max
    lon_min = args.lon_min
    lon_max = args.lon_max
    max_attempts = args.max_attempts
    parallel = args.parallel

    if args.recent > 10:
        print('Getting recent {} minutes files...'.format(args.recent))
        G = GOES(satellite=args.satellite, product=args.product,
                  channel=args.channel)
        df = G.timerange(recent=str(args.recent + 10)+'min', return_as="filelist")
        pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
        df['file'] = "~/data/" + df['file']
        files = df['file'].values
        if parallel:
            # Crop
            with ThreadPoolExecutor(max_workers=args.processes) as executor:
                for _ in executor.map(crop_reproject, files, [output_path]*len(files)):
                    pass
        else:
            for file in files:
                crop_reproject(file, output_path)
        sys.exit()
    else:
        # Process time_range
        time_range = pd.date_range(start=args.start_date, end=args.end_date, freq=args.period)

        # Filtrando o time_range com os argumentos
        time_range = time_range[
            (time_range.hour >= args.between_hours[0]) & 
            (time_range.hour <= args.between_hours[1]) & 
            (time_range.minute >= args.between_minutes[0]) & 
            (time_range.minute <= args.between_minutes[1])
        ]

        # Get goes2go object
        print('Getting GOES2GO object...')
        G = GOES(satellite=args.satellite, product=args.product, channel=args.channel, domain=args.domain)

        # Get df with all files
        df = G.df(start=args.start_date, end=args.end_date)

        # Check if df is empty
        if df.empty:
            print('The args provided did not return any files. Please check the arguments and try again.')
            print(args)
            exit()

        # Filter df by time_range
        print('Filtering files by time range...')
        df['start'] = pd.to_datetime(df['start'])
        # Set index as start
        df.set_index('start', inplace=True)
        df.index = df.index.floor('min')
        # Get files are in time_range and in same interval
        df = df[df.index.isin(time_range)]

        # Check if df is empty
        if df.empty:
            print('The args provided did not return any files. Please check the arguments and try again.')
            print(args)
            exit()

        # Create connection to S3
        print('Creating connection to S3...')
        fs = s3fs.S3FileSystem(anon=True)
        print('Downloading and cropping files...')
        # Set loader
        loading_bar = tqdm.tqdm(total=len(df), ncols=100, position=0, leave=True,
                        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} + \
                        [Elapsed:{elapsed} Remaining:<{remaining}]')
        files = df['file'].values
        times = df.index.to_list()
        
        if args.parallel:
            with ThreadPoolExecutor(max_workers=args.processes) as executor:
                for _ in executor.map(download, zip(files, times)):
                    loading_bar.update(1)
        else:
            for bucket, time in zip(files, times):
                download((bucket, time))
                loading_bar.update(1)

        loading_bar.close()

        # Remove empty folders
        shutil.rmtree(files[0].split('/')[0])


if __name__ == '__main__':
    main()
