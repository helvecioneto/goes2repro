# GOES2REPRO

GOES2REPRO is a utility script that leverages functions from the **goes2go** library, but focuses on downloading, cropping, and reprojecting GOES satellite data.
Allowing users to download data, crop it to a specific geographic area, and reproject it into the EPSG:4326 coordinate reference system.
The script provides flexibility for selecting different products, channels, and satellites, with easy integration for parallel processing.

## Features

- Download and process GOES-16 satellite data from S3 using the **goes2go** library.
- Crop and reproject the data to EPSG:4326 CRS.
- Filter the data by specific time ranges, hours, and minutes.
- Enable parallel processing for faster data handling.
- Output processed data as NetCDF files.
- Log failed downloads to `fail.log`.

## Available Products

The script supports various GOES-16 products, which include different channels and satellites. A full list of available products, channels, and satellites can be found in the [product_table.txt](https://github.com/blaylockbk/goes2go/blob/main/goes2go/product_table.txt).

## Installation

### Prerequisites

You can install the necessary dependencies using `pip`:

```bash
pip install goes2repro
```

## Usage

### Command-Line Arguments

The script uses the `argparse` module for handling command-line arguments. Below are the available options:

```bash
goes2repro [OPTIONS]
```

| Option               | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `--satellite`         | Name of the satellite (e.g., goes16).                                      |
| `--product`           | Name of the satellite product (e.g., ABI-L2-CMIPF). For a list of available products, see [product_table.txt](https://github.com/blaylockbk/goes2go/blob/main/goes2go/product_table.txt). |
| `--var_name`          | Variable name to extract (e.g., CMI).                                       |
| `--channel`           | Channel to use (e.g., 13).                                                   |
| `--start_date`        | Start date in `YYYY-MM-DD HH:MM:SS` format (default: `2022-12-15 00:00:00`).|
| `--end_date`          | End date in `YYYY-MM-DD HH:MM:SS` format (default: `2022-12-15 01:00:00`).  |
| `--period`            | Frequency for the time range (default: `"10 min"`).                         |
| `--between_hours`     | Filter data between these hours (default: `[0, 23]`).                       |
| `--between_minutes`   | Filter data between these minutes (default: `[0, 60]`).                    |
| `--output_path`       | Path for saving output files (default: `output/`).                           |
| `--parallel`          | Enable parallel processing (default: `True`).                               |
| `--processes`         | Number of processes for parallel execution (default: `4`).                  |
| `--lat_min`           | Minimum latitude of the bounding box (default: `-56`).                      |
| `--lat_max`           | Maximum latitude of the bounding box (default: `35`).                       |
| `--lon_min`           | Minimum longitude of the bounding box (default: `-116`).                    |
| `--lon_max`           | Maximum longitude of the bounding box (default: `-25`).                     |
| `--max_attempts`      | Number of attempts to download a file before logging a failure (default: `3`).|

### Examples
To use the script to download and process data for the GOES-16 satellite, ABI-L2-CMIPF product, variable CMI, and channel 13, with a time range of 2022-12-15 from 00:00:00 to 01:00:00, run the following command:


```bash
goes2repro --satellite goes16 --product ABI-L2-CMIPF --var_name CMI --channel 13 --start_date "2022-12-15 00:00:00" --end_date "2022-12-15 01:00:00"
```

To download and process recent 30-minute data for the GOES-16 satellite, ABI-L2-CMIPF product, variable CMI, and channel 13, run the following command:

```bash
goes2repro --satellite goes16 --product ABI-L2-CMIPF --var_name CMI --channel 13 --recent 30 --output_path "output/"
```

### Credits
All the credit goes to the original author of the **goes2go** library.
And this is a otimization by Helvecio Neto - 2025
