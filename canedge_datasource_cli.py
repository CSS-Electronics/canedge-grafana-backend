import json
import logging
import sys
import click
from pathlib import Path
from canedge_datasource import start_server
from canedge_datasource.CanedgeFileSystem import CanedgeFileSystem
from urllib.parse import urlparse
from urllib.request import url2pathname


@click.command()
@click.argument('data_url', envvar='CANEDGE_DATA_URL')
@click.option('--port', required=False, default=5000, type=int, help='The port of the datasource server')
@click.option('--limit', required=False, default=100, type=int, help='Limit on data to process in MB')
@click.option('--s3_ak', required=False, envvar='CANEDGE_S3_AK', type=str, help='S3 access key')
@click.option('--s3_sk', required=False, envvar='CANEDGE_S3_SK', type=str, help='S3 secret key')
@click.option('--s3_bucket', required=False, envvar='CANEDGE_S3_BUCKET', type=str, help='S3 bucket name')
@click.option('--s3_cert', required=False, envvar='CANEDGE_S3_CERT', type=click.Path(), help='S3 cert path')
@click.option('--loglevel', required=False, default="INFO",
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), help='Logging level')
@click.option('--tp_type', required=False, default="", type=str, help='ISO TP type (uds, j1939, nmea)')

def main(data_url, port, limit, s3_ak, s3_sk, s3_bucket, s3_cert, loglevel, tp_type):
    """
    CANedge Grafana Datasource. Provide a URL pointing to a CANedge data root.

    Optionally place decoding rules file(s) (*.dbc) and passwords file (passwords.json) in data source root.

    Example of passwords.json content:

    {"AABBCCDD": "MySecret22BczPassword1234@482", "11223344": "MyOtherSecretPassword512312zZ"}

    Examples

    Scheme: file (local file system)

        OS: Windows

            file:///c:/data/

            file:///c:/Users/bob/Documents/data

            file:///f:/

        OS: Linux:

            file:///home/data/

    Scheme: HTTP (S3):

        http://s3.eu-central-1.amazonaws.com

        http://192.168.0.100

        http://192.168.0.100:5000

    Scheme: HTTPS (S3):

        https://s3.eu-central-1.amazonaws.com

        https://192.168.0.100

        https://192.168.0.100:5000
    """

    # Set log level
    loglevel_number = getattr(logging, loglevel.upper())
    logging.basicConfig(level=loglevel_number, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Set up file system
    print(f"Mount path: {data_url}")
    url = urlparse(data_url)

    # Local file system
    if url.scheme == "file" and url.path != "":
        fs = CanedgeFileSystem(protocol="file", base_path=url2pathname(url.path))

    # S3
    elif url.scheme in ["http", "https"] and url.path == "":
        if s3_ak is None or s3_sk is None or s3_bucket is None:
            sys.exit("Missing S3 information")

        # Server args
        args = {"endpoint_url": data_url}

        # If provided, add cert path
        if s3_cert is not None:
            s3_cert_path = Path(s3_cert)

            # Check if path exist
            if not s3_cert_path.is_file():
                logging.error(f"Cert not found: {s3_cert}")
                sys.exit(-1)

            args["verify"] = s3_cert_path

        fs = CanedgeFileSystem(protocol="s3", base_path=s3_bucket, key=s3_ak, secret=s3_sk, client_kwargs=args, use_listings_cache=False)
    else:
        logging.error(f"Unsupported data URL: {data_url}")
        sys.exit(-1)

    # Load DBs in root
    logging.getLogger("canmatrix").setLevel(logging.ERROR)
    import can_decoder
    dbs = {}
    for db_path in fs.glob("*.dbc"):
        db_name = Path(db_path).stem.lower()
        with fs.open(db_path) as fp:
            db = can_decoder.load_dbc(fp)
            dbs[db_name] = {"db": db, "signals": db.signals()}

    print(f"Loaded DBs: {', '.join(dbs.keys())}")

    # Load passwords file if exists
    passwords = {}
    if fs.isfile("passwords.json"):
        try:
            with fs.open("passwords.json") as fp:
                passwords = json.load(fp)
                print("Loaded passwords file")
        except Exception as e:
            logging.error(f"Unable to load passwords file")
            sys.exit(-1)

    start_server(fs, dbs, passwords, port, limit, tp_type)

if __name__ == '__main__':
    main()
