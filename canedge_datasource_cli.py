import logging
logging.getLogger("canmatrix").setLevel(logging.ERROR)

import sys
import canedge_browser
import can_decoder
import click
from pathlib import Path
from canedge_datasource import start_server
from urllib.parse import urlparse
from urllib.request import url2pathname
from canmatrix.formats import dbc

@click.command()
@click.argument('data_url', envvar='CANEDGE_DATA_URL')
@click.option('--port', required=False, default=5000, type=int, help='The port of the datasource server')
@click.option('--s3_ak', required=False, envvar='CANEDGE_S3_AK', type=str, help='S3 access key')
@click.option('--s3_sk', required=False, envvar='CANEDGE_S3_SK', type=str, help='S3 secret key')
@click.option('--s3_bucket', required=False, envvar='CANEDGE_S3_BUCKET', type=str, help='S3 bucket name')
@click.option('--s3_cert', required=False, envvar='CANEDGE_S3_CERT', type=click.Path(), help='S3 cert path')
@click.option('--debug/--no-debug', required=False, default=False, help='Backend debug')
def main(data_url, port, s3_ak, s3_sk, s3_bucket, s3_cert, debug):
    """
    CANedge Grafana Datasource. Provide a URL pointing to a CANedge data root.

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

    # Set up file system
    url = urlparse(data_url)

    # Local file system
    if url.scheme == "file" and url.path != "":
        fs = canedge_browser.RelativeFileSystem(protocol="file", base_path=url2pathname(url.path))

    # S3
    elif url.scheme in ["http", "https"] and url.path == "":
        if s3_ak is None or s3_sk is None or s3_bucket is None:
            sys.exit("Missing S3 information")

        # Server args
        client_kwargs = {"endpoint_url": data_url}

        # If provided, add cert path
        if s3_cert is not None:
            s3_cert_path = Path(s3_cert)

            # Check if path exist
            if not s3_cert_path.is_file():
                sys.exit(f"Cert not found: {s3_cert}")

            client_kwargs["verify"] = s3_cert_path

        fs = canedge_browser.RelativeFileSystem(protocol="s3",
                                                base_path=s3_bucket,
                                                key=s3_ak,
                                                secret=s3_sk,
                                                client_kwargs=client_kwargs)
    else:
        sys.exit(f"Unsupported data URL: {data_url}")

    # Load DBs in root
    dbs = {}
    for db_path in fs.glob('*.dbc'):
        db_name = Path(db_path).stem.lower()
        with fs.open(db_path) as fp:
            db = can_decoder.load_dbc(fp)
            dbs[db_name] = {"db": db, "signals": db.signals()}

    if debug:
        print("DEBUG MODE")
    print(f"Mount path: {data_url}")
    print(f"Loaded DBs: {', '.join(dbs.keys())}")

    start_server(fs, dbs, port, debug)

if __name__ == '__main__':
    main()
