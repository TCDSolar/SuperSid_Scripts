"""
Process all csv data found within the data path specified in config.cfg,
verifies and creates archive structure before saving the corresponding files to
their specified locations.

@author:
    Oscar Sage David O'Hara
@email:
    oharao@tcd.ie
"""

import os
import shutil
import logging
from pathlib import Path
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta

from supersid.config.config import data_path as config_data, archive_path as config_archive
from supersid.archiver import Archiver
from supersid.vlfclient import VLFClient


def process_file(file, gl=None, gs=None):
    """
    Process single given csv file meeting the appropriate criteria, before
    saving the corresponding png and input csv to the appropriate archive
    location.

    Parameters
    ----------
    file : str
        File path.
    gl : pandas.Series
        GOES XRS Long data.
    gs : pandas.Series
        GOES XRS Short data.

    Returns
    -------
    image_path : str
        Temporary path of generated png.
    """
    if file.endswith('.csv') and not file.__contains__("current") and not file.__contains__(" "):
        vlfclient, archiver = VLFClient(), Archiver(temp_data_path=None)
        logging.debug('The vlfclient and archiver have been initialised.')

        dataframe = vlfclient.read_csv(file)
        header = vlfclient.get_header(dataframe)

        archiver.static_summary_path(header['Site'])

        original_sid = False
        if '-' in header['MonitorID']:
            original_sid = True

        data = vlfclient.get_data(dataframe, original_sid)

        if datetime.strptime(header['UTC_StartTime'], '%Y-%m-%d%H:%M:%S') > datetime.utcnow() - timedelta(days=6):
            image_path = vlfclient.create_plot_xrs(header, data, file, gl, gs, original_sid)
        else:
            image_path = vlfclient.create_plot(header, data, file, original_sid)

        if True == original_sid:
            parents = [(Path(config_archive) / header['Site'].lower() / 'live'),
                       (Path(config_archive) / header['Site'].lower() / 'sid' /
                        datetime.strptime(header['UTC_StartTime'], '%Y-%m-%d%H:%M:%S').strftime('%Y/%m/%d') / 'csv')]
        else:
            parents = [(Path(config_archive) / header['Site'].lower() / 'live'),
                       (Path(config_archive) / header['Site'].lower() / 'super_sid' /
                        datetime.strptime(header['UTC_StartTime'], '%Y-%m-%d%H:%M:%S').strftime('%Y/%m/%d') / 'csv')]

        for path in parents:
            if not path.exists():
                path.mkdir(parents=True)

        if True == original_sid:
            shutil.copy(image_path, parents[0] / (header['StationID'] + '_SID.png'))
        else:
            shutil.copy(image_path, parents[0] / (header['StationID'] + '_SuperSID.png'))
        logging.debug('PNGs copied to archive.')

        shutil.move(Path(file), parents[1] / file.split('/')[-1])
        logging.debug('CSVs moved to archive.')
        return image_path


def process_directory():
    """Function to be run hourly in order to process and archive all files listed
    within the data_path specified within config.cfg."""
    logging.basicConfig(filename='error.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S')
    logging.getLogger('matplotlib.font_manager').disabled = True
    logging.info('Processing called.')

    vlfclient = VLFClient()
    gl, gs = vlfclient.get_recent_goes()

    for directory in config_data:
        for file in os.listdir(directory):
            image = process_file(directory + "/" + file, gl, gs)
            if image:
                logging.debug('%s : Has been processed and archived.', file)
            else:
                logging.warning('%s : Could not be processed.', file)
    logging.info('Processing completed.')

process_directory()  # For development purposes
