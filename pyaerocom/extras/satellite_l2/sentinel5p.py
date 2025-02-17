"""
read Sentinel5P L2 data
"""

import logging
import time

import numpy as np

from pyaerocom import const
from pyaerocom.ungriddeddata import UngriddedData

from .base_reader import ReadL2DataBase


class ReadL2Data(ReadL2DataBase):
    """Interface for reading various Sentinel5P L2 data

    at this point only N2O and Ozone data is (will be) supported

    .. seealso::

        Base class :class:`ReadUngriddedBase`

    """

    _FILEMASK = "*.nc"
    __version__ = "0.02"
    DATA_ID = const.SENTINEL5P_NAME

    # jgliss commented out DATASET_PATH on 22.4.21 since it is not used
    # Note that DATASET_PATH is deprecated as of v0.11.0, use data_dir
    # DATASET_PATH = '/lustre/storeB/project/fou/kl/vals5p/download'
    # Flag if the dataset contains all years or not
    DATASET_IS_YEARLY = False

    _NO2NAME = "tcolno2"
    _O3NAME = "tcolo3"
    _QANAME = "qa_index"
    DEFAULT_VARS = [_O3NAME]
    PROVIDES_VARIABLES = [_NO2NAME, _O3NAME]

    SUPPORTED_DATASETS = []
    SUPPORTED_DATASETS.append(DATA_ID)

    TS_TYPE = "undefined"

    def __init__(
        self,
        data_id=None,
        index_pointer=0,
        loglevel=logging.INFO,
        verbose=False,
        read_averaging_kernel=True,
    ):
        super().__init__(data_id)
        self.verbose = verbose
        self.metadata = {}
        self.data = None
        self.data_for_gridding = {}
        self.gridded_data = {}
        self.global_attributes = {}
        self.index = len(self.metadata)
        self.files = []
        self.files_read = []
        self.index_pointer = index_pointer
        # that's the flag to indicate if the location of a data point in self.data has been
        # stored in rads in self.data already
        # trades RAM for speed
        self.rads_in_array_flag = False
        # these are the variable specific attributes written into a netcdf file
        self._TIME_OFFSET_NAME = "delta_time"
        self._NO2NAME = "tcolno2"
        self._O3NAME = "tcolo3"
        self._QANAME = "qa_index"
        self._SCANLINENAME = "scanline"
        self._GROUNDPIXELNAME = "ground_pixel"

        self._LATBOUNDSNAME = "lat_bnds"
        self._LATBOUNDSSIZE = 4
        self._LONBOUNDSNAME = "lon_bnds"
        self._LONBOUNDSSIZE = 4
        self.COORDINATE_NAMES = [
            self._LATITUDENAME,
            self._LONGITUDENAME,
            self._ALTITUDENAME,
            self._LATBOUNDSNAME,
            self._LONBOUNDSNAME,
            self._LEVELSNAME,
            self._TIME_NAME,
        ]

        self._QAINDEX = UngriddedData._DATAFLAGINDEX
        self._TIME_OFFSET_INDEX = UngriddedData._TRASHINDEX
        self._LATBOUNDINDEX = 13
        self._LONBOUNDINDEX = self._LATBOUNDINDEX + self._LATBOUNDSSIZE + 1
        self._COLNO = self._LATBOUNDINDEX + self._LATBOUNDSSIZE + self._LONBOUNDSSIZE + 2
        self._HEIGHTSTEPNO = 24
        self.SUPPORTED_SUFFIXES.append(".nc")

        # create a dict with the aerocom variable name as key and the index number in the
        # resulting numpy array as value.
        # INDEX_DICT = {}
        self.INDEX_DICT.update({self._LATITUDENAME: self._LATINDEX})
        self.INDEX_DICT.update({self._LONGITUDENAME: self._LONINDEX})
        self.INDEX_DICT.update({self._ALTITUDENAME: self._ALTITUDEINDEX})
        self.INDEX_DICT.update({self._TIME_NAME: self._TIMEINDEX})
        self.INDEX_DICT.update({self._TIME_OFFSET_NAME: self._TIME_OFFSET_INDEX})
        self.INDEX_DICT.update({self._NO2NAME: self._DATAINDEX01})
        self.INDEX_DICT.update({self._O3NAME: self._DATAINDEX01})
        self.INDEX_DICT.update({self._QANAME: self._QAINDEX})
        self.INDEX_DICT.update({self._LATBOUNDSNAME: self._LATBOUNDINDEX})
        self.INDEX_DICT.update({self._LONBOUNDSNAME: self._LONBOUNDINDEX})

        # dictionary to store array sizes of an element in self.data
        # SIZE_DICT = {}
        self.SIZE_DICT.update({self._LATBOUNDSNAME: self._LATBOUNDSSIZE})
        self.SIZE_DICT.update({self._LONBOUNDSNAME: self._LONBOUNDSSIZE})

        # NaN values are variable specific
        # NAN_DICT = {}
        self.NAN_DICT.update({self._LATITUDENAME: -1.0e-6})
        self.NAN_DICT.update({self._LONGITUDENAME: -1.0e-6})
        self.NAN_DICT.update({self._ALTITUDENAME: -1.0})

        # scaling factors e.g. for unit conversion
        self.SCALING_FACTORS[self._NO2NAME] = np.float64(6.022140857e19 / 1.0e15)

        # the following defines necessary quality flags for a value to make it into the used data set
        # the flag needs to have a HIGHER or EQUAL value than the one listed here
        # The valuse are taken form the product readme file
        # QUALITY_FLAGS = {}
        self.QUALITY_FLAGS.update({self._NO2NAME: 0.75})
        # QUALITY_FLAGS.update({_NO2NAME: 0.5}) #cloudy
        self.QUALITY_FLAGS.update({self._O3NAME: 0.7})

        self.CODA_READ_PARAMETERS[self._NO2NAME] = {}
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"] = {}
        self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"] = {}
        self.CODA_READ_PARAMETERS[self._NO2NAME]["time_offset"] = np.float64(24.0 * 60.0 * 60.0)
        self.CODA_READ_PARAMETERS[self._O3NAME] = {}
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"] = {}
        self.CODA_READ_PARAMETERS[self._O3NAME]["vars"] = {}
        self.CODA_READ_PARAMETERS[self._O3NAME]["time_offset"] = np.float64(24.0 * 60.0 * 60.0)

        # self.CODA_READ_PARAMETERS[DATASET_NAME]['metadata'][_TIME_NAME] = 'PRODUCT/time_utc'
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._TIME_NAME] = "PRODUCT/time"
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._TIME_OFFSET_NAME] = (
            "PRODUCT/delta_time"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._LATITUDENAME] = (
            "PRODUCT/latitude"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._LONGITUDENAME] = (
            "PRODUCT/longitude"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._SCANLINENAME] = (
            "PRODUCT/scanline"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._GROUNDPIXELNAME] = (
            "PRODUCT/ground_pixel"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._LONBOUNDSNAME] = (
            "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/longitude_bounds"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._LATBOUNDSNAME] = (
            "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/latitude_bounds"
        )
        self.CODA_READ_PARAMETERS[self._NO2NAME]["metadata"][self._QANAME] = "PRODUCT/qa_value"
        self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._NO2NAME] = (
            "PRODUCT/nitrogendioxide_tropospheric_column"
        )

        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._TIME_NAME] = "PRODUCT/time"
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._TIME_OFFSET_NAME] = (
            "PRODUCT/delta_time"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._LATITUDENAME] = (
            "PRODUCT/latitude"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._LONGITUDENAME] = (
            "PRODUCT/longitude"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._LONBOUNDSNAME] = (
            "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/longitude_bounds"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._LATBOUNDSNAME] = (
            "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/latitude_bounds"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._SCANLINENAME] = (
            "PRODUCT/scanline"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._GROUNDPIXELNAME] = (
            "PRODUCT/ground_pixel"
        )
        self.CODA_READ_PARAMETERS[self._O3NAME]["metadata"][self._QANAME] = "PRODUCT/qa_value"
        self.CODA_READ_PARAMETERS[self._O3NAME]["vars"][self._O3NAME] = (
            "PRODUCT/ozone_total_vertical_column"
        )

        ####################################
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME] = {}
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]["_FillValue"] = np.nan
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]["long_name"] = (
            "Tropospheric vertical column of nitrogen dioxide"
        )
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]["standard_name"] = (
            "troposphere_mole_content_of_nitrogen_dioxide"
        )
        # self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]['units'] = 'mol m-2'
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]["units"] = "1e15 molecules cm-2"
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME]["coordinates"] = "longitude latitude"

        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_mean"] = self.NETCDF_VAR_ATTRIBUTES[
            self._NO2NAME
        ]

        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_numobs"] = {}
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_numobs"]["_FillValue"] = np.nan
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_numobs"]["long_name"] = (
            "number of observations"
        )
        # self.NETCDF_VAR_ATTRIBUTES[_NO2NAME+'_numobs'][
        #     'standard_name'] = 'troposphere_mole_content_of_nitrogen_dioxide'
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_numobs"]["units"] = "1"
        self.NETCDF_VAR_ATTRIBUTES[self._NO2NAME + "_numobs"]["coordinates"] = "longitude latitude"

        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"] = {}
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"]["_FillValue"] = np.nan
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"]["long_name"] = (
            "total vertical ozone column"
        )
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"]["standard_name"] = (
            "atmosphere_mole_content_of_ozone"
        )
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"]["units"] = "mol m-2"
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_mean"]["coordinates"] = "longitude latitude"

        # used for L2 writing
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME] = self.NETCDF_VAR_ATTRIBUTES[
            self._O3NAME + "_mean"
        ]

        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_numobs"] = {}
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_numobs"]["_FillValue"] = np.nan
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_numobs"]["long_name"] = (
            "number of observations"
        )
        # self.NETCDF_VAR_ATTRIBUTES[_O3NAME+'_numobs'][
        #     'standard_name'] = 'troposphere_mole_content_of_nitrogen_dioxide'
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_numobs"]["units"] = "1"
        self.NETCDF_VAR_ATTRIBUTES[self._O3NAME + "_numobs"]["coordinates"] = "longitude latitude"

        self.NETCDF_VAR_ATTRIBUTES[self._QANAME] = {}
        self.NETCDF_VAR_ATTRIBUTES[self._QANAME]["_FillValue"] = np.nan
        self.NETCDF_VAR_ATTRIBUTES[self._QANAME]["long_name"] = "data quality value"
        self.NETCDF_VAR_ATTRIBUTES[self._QANAME]["comment"] = (
            "A continuous quality descriptor, varying between 0(no data) and 1 (full quality data). Recommend to ignore data with qa_value < 0.5"
        )
        self.NETCDF_VAR_ATTRIBUTES[self._QANAME]["units"] = "1"
        self.NETCDF_VAR_ATTRIBUTES[self._QANAME]["coordinates"] = "longitude latitude"

        if read_averaging_kernel:
            # reading the averaging kernel needs some more data fields
            self._AVERAGINGKERNELNAME = "avg_kernel"
            self._AVERAGINGKERNELSIZE = 34
            self._AVERAGINGKERNELINDEX = self._LONBOUNDINDEX + self._LONBOUNDSSIZE + 1
            self._GROUNDPRESSURENAME = "p0"
            self._GROUNDPRESSUREINDEX = self._AVERAGINGKERNELINDEX + self._AVERAGINGKERNELSIZE
            self._LEVELSNAME = "levels"
            self._LEVELSSIZE = self._AVERAGINGKERNELSIZE
            self._LEVELSINDEX = self._GROUNDPRESSUREINDEX + 1
            self._TM5_TROPOPAUSE_LAYER_INDEX_NAME = "tm5_tropopause_layer_index"
            self._TM5_TROPOPAUSE_LAYER_INDEX_INDEX = self._LEVELSINDEX + self._LEVELSSIZE + 1
            self._TM5_CONSTANT_A_NAME = "tm5_constant_a"
            self._TM5_CONSTANT_A_INDEX = self._TM5_TROPOPAUSE_LAYER_INDEX_INDEX + 1
            self._TM5_CONSTANT_B_NAME = "tm5_constant_b"
            self._TM5_CONSTANT_B_INDEX = self._TM5_CONSTANT_A_INDEX + 1

            self._COLNO = self._TM5_CONSTANT_B_INDEX + 1
            self.INDEX_DICT.update({self._AVERAGINGKERNELNAME: self._AVERAGINGKERNELINDEX})
            self.INDEX_DICT.update({self._LEVELSNAME: self._LEVELSINDEX})
            self.INDEX_DICT.update({self._GROUNDPRESSURENAME: self._GROUNDPRESSUREINDEX})
            self.INDEX_DICT.update(
                {self._TM5_TROPOPAUSE_LAYER_INDEX_NAME: self._TM5_TROPOPAUSE_LAYER_INDEX_INDEX}
            )
            self.INDEX_DICT.update({self._TM5_CONSTANT_A_NAME: self._TM5_CONSTANT_A_INDEX})
            self.INDEX_DICT.update({self._TM5_CONSTANT_B_NAME: self._TM5_CONSTANT_B_INDEX})

            self.SIZE_DICT.update({self._AVERAGINGKERNELNAME: self._AVERAGINGKERNELSIZE})
            self.SIZE_DICT.update({self._LEVELSNAME: self._LEVELSSIZE})

            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME] = {}
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["time_offset"] = np.float64(
                24.0 * 60.0 * 60.0
            )
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][self._TIME_NAME] = (
                "PRODUCT/time"
            )
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._TIME_OFFSET_NAME
            ] = "PRODUCT/delta_time"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._LATITUDENAME
            ] = "PRODUCT/latitude"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._LONGITUDENAME
            ] = "PRODUCT/longitude"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._SCANLINENAME
            ] = "PRODUCT/scanline"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._GROUNDPIXELNAME
            ] = "PRODUCT/ground_pixel"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._LONBOUNDSNAME
            ] = "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/longitude_bounds"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][
                self._LATBOUNDSNAME
            ] = "PRODUCT/SUPPORT_DATA/GEOLOCATIONS/latitude_bounds"
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["metadata"][self._QANAME] = (
                "PRODUCT/qa_value"
            )
            self.CODA_READ_PARAMETERS[self._AVERAGINGKERNELNAME]["vars"][
                self._AVERAGINGKERNELNAME
            ] = "PRODUCT/averaging_kernel"

            self.CODA_READ_PARAMETERS[self._LEVELSNAME] = {}
            self.CODA_READ_PARAMETERS[self._LEVELSNAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._LEVELSNAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._LEVELSNAME]["time_offset"] = np.float64(
                24.0 * 60.0 * 60.0
            )
            self.CODA_READ_PARAMETERS[self._LEVELSNAME]["vars"][self._LEVELSNAME] = "PRODUCT/layer"

            self.CODA_READ_PARAMETERS[self._GROUNDPRESSURENAME] = {}
            self.CODA_READ_PARAMETERS[self._GROUNDPRESSURENAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._GROUNDPRESSURENAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._GROUNDPRESSURENAME]["time_offset"] = np.float64(
                24.0 * 60.0 * 60.0
            )
            self.CODA_READ_PARAMETERS[self._GROUNDPRESSURENAME]["vars"][
                self._GROUNDPRESSURENAME
            ] = "PRODUCT/SUPPORT_DATA/INPUT_DATA/surface_pressure"

            self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME] = {}
            self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME]["time_offset"] = (
                np.float64(24.0 * 60.0 * 60.0)
            )
            self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME]["vars"][
                self._TM5_TROPOPAUSE_LAYER_INDEX_NAME
            ] = "PRODUCT/tm5_tropopause_layer_index"

            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_A_NAME] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_A_NAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_A_NAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_A_NAME]["time_offset"] = np.float64(
                24.0 * 60.0 * 60.0
            )
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_A_NAME]["vars"][
                self._TM5_CONSTANT_A_NAME
            ] = "PRODUCT/tm5_constant_a"
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_B_NAME] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_B_NAME]["metadata"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_B_NAME]["vars"] = {}
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_B_NAME]["time_offset"] = np.float64(
                24.0 * 60.0 * 60.0
            )
            self.CODA_READ_PARAMETERS[self._TM5_CONSTANT_B_NAME]["vars"][
                self._TM5_CONSTANT_B_NAME
            ] = "PRODUCT/tm5_constant_b"

            self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME] = {}
            self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME]["_FillValue"] = np.nan
            self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME]["long_name"] = "averaging kernel"
            # self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME]['standard_name'] = 'averaging_kernel'
            self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME]["units"] = "1"
            self.NETCDF_VAR_ATTRIBUTES[self._AVERAGINGKERNELNAME]["coordinates"] = (
                f"longitude latitude {self._LEVELSNAME}"
            )

            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._LEVELSNAME] = (
                self.CODA_READ_PARAMETERS[self._LEVELSNAME]["vars"][self._LEVELSNAME]
            )
            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._GROUNDPRESSURENAME] = (
                self.CODA_READ_PARAMETERS[
                    self._GROUNDPRESSURENAME
                ]["vars"][self._GROUNDPRESSURENAME]
            )
            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][
                self._TM5_TROPOPAUSE_LAYER_INDEX_NAME
            ] = self.CODA_READ_PARAMETERS[self._TM5_TROPOPAUSE_LAYER_INDEX_NAME]["vars"][
                self._TM5_TROPOPAUSE_LAYER_INDEX_NAME
            ]
            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._TM5_CONSTANT_A_NAME] = (
                self.CODA_READ_PARAMETERS[
                    self._TM5_CONSTANT_A_NAME
                ]["vars"][self._TM5_CONSTANT_A_NAME]
            )
            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._TM5_CONSTANT_B_NAME] = (
                self.CODA_READ_PARAMETERS[
                    self._TM5_CONSTANT_B_NAME
                ]["vars"][self._TM5_CONSTANT_B_NAME]
            )
            self.CODA_READ_PARAMETERS[self._NO2NAME]["vars"][self._AVERAGINGKERNELNAME] = (
                self.CODA_READ_PARAMETERS[
                    self._AVERAGINGKERNELNAME
                ]["vars"][self._AVERAGINGKERNELNAME]
            )

        self.STATICFIELDNAMES = [
            self._GROUNDPIXELNAME,
            self._LEVELSNAME,
            self._TM5_CONSTANT_A_NAME,
            self._TM5_CONSTANT_B_NAME,
        ]

        # field name whose size determines the number of time steps in a product
        self.TSSIZENAME = self._TIME_OFFSET_NAME

        # ensure logging shows this file
        self.logger = logging.getLogger(__name__)
        if loglevel is not None:
            # if self.logger.hasHandlers():
            #     # Logger is already configured, remove all handlers
            #     self.logger.handlers = []
            # # self.logger = logging.getLogger('pyaerocom')
            # default_formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
            # console_handler = logging.StreamHandler()
            # console_handler.setFormatter(default_formatter)
            # self.logger.addHandler(console_handler)
            self.logger.setLevel(loglevel)

    ###################################################################################
    def read_file(
        self,
        filename,
        vars_to_retrieve=["tcolno2"],
        return_as="dict",
        loglevel=None,
        apply_quality_flag=True,
        colno=None,
        read_avg_kernel=True,
    ):
        """method to read the file a Sentinel 5P data file

        Parameters
        ----------
        filename : str
            absolute path to filename to read
        vars_to_retrieve : str
            str with variable name to read; defaults to ['tcolno2']
        return_as:
            either 'dict' or 'numpy'; defaults to 'dict'
        loglevel:
            loglevel as for the logging module.
            Since the reading can take some time logging.INFO is recommended
        apply_quality_flag:
            apply the quality flag from the data product; True or False; defaults to True
        colno : int
            # of columns to return in case the return_as parameter is 'numpy'
            In it's extended form this object can also return the lat and lon bounds of the location.
            Unfortunately that adds another 8 rows to the entire data array which might be too memory heavy
            and is onluy needed if the data ins converted to netcdf at this point. So we keep this optional for now
            since the netcdf export is nor yet implemented in pyaerocom.
            if colno < _COLNO the bounds will not be returned in the numpy array
        read_avg_kernel : bool
            also read the averaging kernel
            default: True

        Returns
        --------
        Either:
            dictionary (default):
                keys are 'time', 'latitude', 'longitude', 'altitude' and the variable name
                ('tcolno2' or 'tcolo3' at this point if the whole file is read

            2d ndarray of type float:
                representing a 'point cloud' with all points
                    column 1: time in seconds since the Unix epoch with ms accuracy (same time for every point in the
                              swath)
                    column 2: latitude
                    column 3: longitude
                    column 4: altitude

                    Note: negative values are put to np.nan already

        """

        if colno is None:
            colno = self._COLNO

        import coda

        start = time.perf_counter()
        file_data = {}

        self.logger.info(f"reading file {filename}")
        # read file
        product = coda.open(filename)

        if isinstance(vars_to_retrieve, str):
            read_dataset = [vars_to_retrieve]
        vars_to_read_in = None
        vars_to_read_in = vars_to_retrieve.copy()

        # This is for Sentinel 5p netcdf files read via coda to avoid dealing with all the groups in there
        # coda for S5P uses 2010-01-01T00:00:00 as epoch unfortunately.
        # so calculate the difference in seconds to the Unix epoch
        seconds_to_add = np.datetime64("2010-01-01T00:00:00") - np.datetime64(
            "1970-01-01T00:00:00"
        )
        seconds_to_add = seconds_to_add.astype(np.float64)

        # the same can be achieved using pandas, but we stick to numpy here
        # base_time = pd.DatetimeIndex(['2000-01-01'])
        # seconds_to_add = (base_time.view('int64') // pd.Timedelta(1, unit='s'))[0]

        # if vars_to_retrieve[0] is None:
        #     # read all variables
        #     vars_to_read_in = list(self.CODA_READ_PARAMETERS[vars_to_retrieve[0]]['vars'])
        for _vars in vars_to_retrieve:
            vars_to_read_in.extend(list(self.CODA_READ_PARAMETERS[_vars]["vars"]))
            vars_to_read_in.extend(list(self.CODA_READ_PARAMETERS[_vars]["metadata"]))
        # get rid of duplicates
        vars_to_read_in = list(set(vars_to_read_in))

        # read data time
        # it consists of the base time of the orbit and an offset per scanline

        coda_groups_to_read = self.CODA_READ_PARAMETERS[vars_to_retrieve[0]]["metadata"][
            self._TIME_NAME
        ].split(self.GROUP_DELIMITER)

        # seconds since 1 Jan 2010
        time_data_temp = coda.fetch(product, coda_groups_to_read[0], coda_groups_to_read[1])
        file_data[self._TIME_NAME] = (
            ((time_data_temp + seconds_to_add) * 1.0e3).astype(np.int).astype("datetime64[ms]")
        )

        # read the offset per scanline
        coda_groups_to_read = self.CODA_READ_PARAMETERS[vars_to_retrieve[0]]["metadata"][
            self._TIME_OFFSET_NAME
        ].split(self.GROUP_DELIMITER)

        # the result in in milli seconds an can therefore just added to the base time
        time_data_temp = coda.fetch(product, coda_groups_to_read[0], coda_groups_to_read[1])
        file_data[self._TIME_OFFSET_NAME] = file_data[self._TIME_NAME] + np.squeeze(time_data_temp)

        # read data in a simple dictionary
        for var in vars_to_read_in:
            # time has been read already
            if var == self._TIME_NAME or var == self._TIME_OFFSET_NAME:
                continue
            self.logger.info(f"reading var: {var}")

            try:
                groups = self.CODA_READ_PARAMETERS[vars_to_retrieve[0]]["metadata"][var].split(
                    self.GROUP_DELIMITER
                )
            except KeyError:
                groups = self.CODA_READ_PARAMETERS[vars_to_retrieve[0]]["vars"][var].split(
                    self.GROUP_DELIMITER
                )

            # the data comes as record and not as array as at aeolus
            file_data[var] = {}

            if len(groups) == 3:
                file_data[var] = np.squeeze(coda.fetch(product, groups[0], groups[1], groups[2]))

            elif len(groups) == 2:
                file_data[var] = np.squeeze(coda.fetch(product, groups[0], groups[1]))
            elif len(groups) == 4:
                file_data[var] = np.squeeze(
                    coda.fetch(product, groups[0], groups[1], groups[2], groups[3])
                )
            else:
                file_data[var] = np.squeeze(coda.fetch(product, groups[0]))

            if var in self.SCALING_FACTORS:
                file_data[var] = file_data[var] * self.SCALING_FACTORS[var]

        coda.close(product)

        if return_as == "numpy":
            # return as one multidimensional numpy array that can be put into self.data directly
            # (column wise because the column numbers do not match)
            index_pointer = 0
            data = np.empty([self._ROWNO, colno], dtype=np.float64)
            # loop over the times
            for idx, _time in enumerate(file_data[self._TIME_OFFSET_NAME]):
                # loop over the number of ground pixels
                for _index in range(file_data[self._LATITUDENAME].shape[1]):
                    # check first if the quality flag requirement is met

                    if (
                        apply_quality_flag
                        and file_data[self._QANAME][idx, _index]
                        < self.QUALITY_FLAGS[vars_to_retrieve[0]]
                    ):
                        # potential debugging...
                        # if _index < 100:
                        #     print(file_data[self._QANAME][idx,_index])
                        continue

                    # time can be a scalar...
                    try:
                        data[index_pointer, self._TIMEINDEX] = _time.astype(np.float64)
                    except Exception:
                        data[index_pointer, self._TIMEINDEX] = _time[_index].astype(np.float64)

                    # loop over the variables
                    for var in vars_to_read_in:
                        # time is the index, so skip it here
                        if var == self._TIME_NAME or var == self._TIME_OFFSET_NAME:
                            continue
                        # the bounds need to be treated special

                        elif colno == self._COLNO and var in self.SIZE_DICT:
                            data[
                                index_pointer,
                                self.INDEX_DICT[var] : self.INDEX_DICT[var] + self.SIZE_DICT[var],
                            ] = file_data[var][idx, _index]
                        else:
                            data[index_pointer, self.INDEX_DICT[var]] = file_data[var][idx, _index]

                    index_pointer += 1
                    if index_pointer >= self._ROWNO:
                        # add another array chunk to self.data
                        data = np.append(
                            data,
                            np.empty([self._CHUNKSIZE, self._COLNO], dtype=np.float64),
                            axis=0,
                        )
                        # unneeded after update (_ROWNO is now dynamic and returns shape index 0 of numpy array)
                        # self._ROWNO += self._CHUNKSIZE

            # return only the needed elements...
            file_data = data[0:index_pointer]

        end_time = time.perf_counter()
        elapsed_sec = end_time - start
        temp = f"time for single file read [s]: {elapsed_sec:.3f}"
        self.logger.info(temp)
        # self.logger.info('{} points read'.format(index_pointer))
        self.files_read.append(filename)
        return file_data

    ###################################################################################

    def to_netcdf_simple(
        self,
        netcdf_filename="/home/jang/tmp/to_netcdf_simple.nc",
        global_attributes=None,
        vars_to_write=None,
        data_to_write=None,
        gridded=False,
        apply_quality_flag=0.0,
    ):
        if data_to_write is None:
            _data = self.data
        else:
            try:
                _data = data_to_write._data
            except AttributeError:
                _data = data_to_write

        if isinstance(_data, dict):
            # write out the read data using the dictionary directly
            vars_to_write_out = vars_to_write.copy()
            if isinstance(vars_to_write_out, str):
                vars_to_write_out = [vars_to_write_out]

            ds = self.to_xarray(_data, gridded=gridded, apply_quality_flag=apply_quality_flag)

            # add potential global attributes
            try:
                for name in global_attributes:
                    ds.attrs[name] = global_attributes[name]
            except Exception:
                pass

            obj.logger.info(f"writing file {netcdf_filename}...")
            # compress the main variables
            encoding = {}
            if self._NO2NAME in ds:
                encoding[self._NO2NAME] = {"zlib": True, "complevel": 5}
            if self._AVERAGINGKERNELNAME in ds:
                encoding[self._AVERAGINGKERNELNAME] = {"zlib": True, "complevel": 5}
            if self._O3NAME in ds:
                encoding[self._O3NAME] = {"zlib": True, "complevel": 5}
            # encoding[self._O3NAME] = {'zlib': True,'complevel': 5}
            ds.to_netcdf(netcdf_filename, encoding=encoding)
            # ds.to_netcdf(netcdf_filename)
            obj.logger.info(f"file {netcdf_filename} written")
        else:
            # call super class
            super().to_netcdf_simple(
                netcdf_filename, global_attributes, vars_to_write, data_to_write, gridded
            )

    ###################################################################################
    def _match_dim_name(self, dim_dict, dim_size=None, data=None):
        """small helper routine to match the dimension size to a dimension name"""

        # try to match the shapes to the dimensions
        ret_data = {}

        if data is not None:
            for var in data:
                ret_data[var] = []
                # not all is a ndarray with a shape
                try:
                    shape = data[var].shape
                except Exception:
                    continue

                for _size in data[var].shape:
                    try:
                        ret_data[var].append(dim_dict[_size])
                    except Exception:
                        pass
            return ret_data
        else:
            return dim_dict[dim_size]

    ###################################################################################

    def to_xarray(self, data_to_write=None, gridded=False, apply_quality_flag=0.0):
        """helper method to turn a read dictionary into an xarray dataset opbject"""

        if isinstance(data_to_write, dict):
            _data = data_to_write
        else:
            _data = data_to_write._data

        import numpy as np
        import xarray as xr

        bounds_dim_name = "bounds"
        bounds_dim_size = 4
        level_dim_name = self._LEVELSNAME
        level_dim_size = self._LEVELSSIZE

        if not gridded:
            # vars_to_write_out.extend(list(self.CODA_READ_PARAMETERS[vars_to_write[0]]['metadata']))
            # var_write_out = _data.keys()

            # datetimedata = pd.to_datetime(_data[:, self._TIMEINDEX].astype('datetime64[s]'))
            # build the datetimedata...
            ts_no = len(_data["scanline"])
            swath_width = len(_data["ground_pixel"])
            point_dim_len = ts_no * swath_width
            datetimedata = np.empty(point_dim_len)
            point_dim_name = "point"
            point_dim_size = point_dim_len
            swath_dim_name = self._GROUNDPIXELNAME
            swath_dim_size = swath_width
            tm5_constant_dim_name = "const_dim"
            tm5_constant_dim_size = 2
            # scanline_dim_name = self._SCANLINENAME
            # scanline_dim_size = ts_no
            for idx, _time in enumerate(_data["delta_time"]):
                # print('range: {} to {}'.format(idx*swath_width,(idx+1)*swath_width-1))
                datetimedata[idx * swath_width : (idx + 1) * swath_width] = _data["delta_time"][
                    idx
                ]
                # datetimedata[idx*swath_width:(idx+1)*swath_width] = _data['delta_time'].astype('datetime64[ms]')
            # datetimedata = pd.to_datetime(_data[:, self._TIMEINDEX].astype('datetime64[ms]'))
            # pointnumber = np.arange(0, len(datetimedata))
            ds = xr.Dataset()

            # time and potentially levels are special variables that needs special treatment
            ds[self._TIME_NAME] = (point_dim_name), datetimedata.astype("datetime64[ms]")
            skip_vars = [self._TIME_NAME, self._SCANLINENAME]
            skip_vars.extend(["delta_time"])
            ds[self._LEVELSNAME] = (level_dim_name), np.arange(self._LEVELSSIZE)
            skip_vars.extend([self._LEVELSNAME])
            ds[self._GROUNDPIXELNAME] = (swath_dim_name), _data["ground_pixel"]
            skip_vars.extend([self._GROUNDPIXELNAME])
            ds[point_dim_name] = np.arange(point_dim_len)
            ds[tm5_constant_dim_name] = np.arange(tm5_constant_dim_size)
            ds[bounds_dim_name] = np.arange(4)

            # define a dict with the dimension size as key and the dimensions name as value
            dim_size_dict = {}
            dim_size_dict[point_dim_size] = point_dim_name
            dim_size_dict[bounds_dim_size] = bounds_dim_name
            dim_size_dict[swath_dim_size] = swath_dim_name
            dim_size_dict[level_dim_size] = level_dim_name
            dim_size_dict[tm5_constant_dim_size] = tm5_constant_dim_name
            # dim_size_dict[scanline_dim_size] = scanline_dim_name

            dim_name_dict = self._match_dim_name(dim_size_dict, data=_data)
            if apply_quality_flag > 0.0:
                # apply quality flags on the point cloud
                qflags = _data[self._QANAME].reshape(point_dim_len)
                keep_indexes = np.where(qflags >= apply_quality_flag)
                elements_to_add = len(keep_indexes[0])
                # dim_size_dict[elements_to_add] = point_dim_name
                ds = xr.Dataset()
                ds[self._TIME_NAME] = (
                    (point_dim_name),
                    datetimedata.astype("datetime64[ms]")[keep_indexes],
                )
                ds[point_dim_name] = np.arange(elements_to_add)
                # point_dim_size = elements_to_add

            for var in _data:
                # loop through the variables
                if var in skip_vars:
                    continue
                try:
                    shape = _data[var].shape
                except AttributeError:
                    continue
                print(f"variable: {var}")
                if len(_data[var].shape) == 1:
                    # var with dimension time (e.g. 3245)
                    # each time needs to be repeated by the swath width
                    if apply_quality_flag == 0.0:
                        try:
                            ds[var] = (point_dim_name), _data[var]
                        except ValueError:
                            ds[var] = (dim_size_dict[_data[var].shape[0]]), _data[var]
                    else:
                        try:
                            ds[var] = (point_dim_name), _data[var][keep_indexes]
                        except ValueError:
                            ds[var] = (
                                (dim_size_dict[_data[var].shape[0]]),
                                _data[var][keep_indexes],
                            )

                elif len(_data[var].shape) == 2:
                    # var with dimension time and swath (e.g. 3245, 450)
                    if apply_quality_flag == 0.0:
                        try:
                            ds[var] = (point_dim_name), _data[var].reshape(point_dim_len)
                        except ValueError:
                            ds[var] = (dim_name_dict[var]), _data[var]
                    else:
                        try:
                            ds[var] = (
                                (point_dim_name),
                                (_data[var].reshape(point_dim_len))[keep_indexes],
                            )
                        except ValueError:
                            ds[var] = (dim_name_dict[var]), _data[var]

                elif len(_data[var].shape) == 3:
                    # var with dimension time, swath and levels or bounds
                    # store some vars depending on the points dimension as a 2d variable
                    if apply_quality_flag == 0.0:
                        if var == "avg_kernel":
                            ds[var] = (
                                (point_dim_name, level_dim_name),
                                _data[var].reshape([point_dim_size, level_dim_size]),
                            )
                        elif var == "lat_bnds" or var == "lon_bnds":
                            ds[var] = (
                                (point_dim_name, bounds_dim_name),
                                _data[var].reshape([point_dim_size, bounds_dim_size]),
                            )
                        else:
                            ds[var] = (dim_name_dict[var]), _data[var]
                    else:
                        if var == "avg_kernel":
                            # temp = np.squeeze((_data[var].reshape([point_dim_size, level_dim_size]))[keep_indexes,:])
                            ds[var] = (
                                (point_dim_name, level_dim_name),
                                np.squeeze(
                                    (_data[var].reshape([point_dim_size, level_dim_size]))[
                                        keep_indexes, :
                                    ]
                                ),
                            )
                            print(f"{var}")

                        elif var == "lat_bnds" or var == "lon_bnds":
                            ds[var] = (
                                (point_dim_name, bounds_dim_name),
                                np.squeeze(
                                    _data[var].reshape([point_dim_size, bounds_dim_size])[
                                        keep_indexes, :
                                    ]
                                ),
                            )
                        else:
                            ds[var] = (dim_name_dict[var]), _data[var]

            # add attributes to variables
            for var in ds:
                # add predifined attributes
                print(f"var {var}")
                try:
                    for attrib in self.NETCDF_VAR_ATTRIBUTES[var]:
                        ds[var].attrs[attrib] = self.NETCDF_VAR_ATTRIBUTES[var][attrib]
                except KeyError:
                    pass

        else:
            # gridded
            time_dim_name = self._TIME_NAME
            lat_dim_name = self._LATITUDENAME
            lon_dim_name = self._LONGITUDENAME

            ds = xr.Dataset()

            # temp = 15 + 8 * np.random.randn(2, 2, 3)
            # ds = xr.Dataset({'temperature': (['x', 'y', 'time'],  temp),
            #    ....:                  'precipitation': (['x', 'y', 'time'], precip)},
            #    ....:                 coords={'lon': (['x', 'y'], lon),
            #    ....:                         'lat': (['x', 'y'], lat),
            #    ....:                         'time': pd.date_range('2014-09-06', periods=3),
            #    ....:                         'reference_time': pd.Timestamp('2014-09-05')})
            # coordinate variables need special treatment

            ds[time_dim_name] = np.array(_data[time_dim_name].astype("datetime64[D]"))
            ds[lat_dim_name] = (
                (lat_dim_name),
                _data[lat_dim_name],
            )
            ds[lon_dim_name] = (lon_dim_name), _data[lon_dim_name]

            # for var in vars_to_write_out:
            for var in data_to_write:
                if var in self.COORDINATE_NAMES:
                    # if var == self._TIME_NAME:
                    continue
                # 1D data
                # 3D data
                ds[var + "_mean"] = (
                    (lat_dim_name, lon_dim_name),
                    np.reshape(
                        _data[var]["mean"], (len(_data[lat_dim_name]), len(_data[lon_dim_name]))
                    ),
                )
                ds[var + "_numobs"] = (
                    (lat_dim_name, lon_dim_name),
                    np.reshape(
                        _data[var]["numobs"], (len(_data[lat_dim_name]), len(_data[lon_dim_name]))
                    ),
                )

            # add attributes to variables
            for var in ds.variables:
                # add predifined attributes
                print(f"var {var}")
                try:
                    for attrib in self.NETCDF_VAR_ATTRIBUTES[var]:
                        ds[var].attrs[attrib] = self.NETCDF_VAR_ATTRIBUTES[var][attrib]
                except KeyError:
                    pass

        # remove _FillValue attribute from coordinate variables since that
        # is forbidden by CF convention
        for var in self.COORDINATE_NAMES:
            # if var in self.COORDINATE_NAMES:
            try:
                del ds[var].encoding["_FillValue"]
            except KeyError:
                pass

            # # add predifined attributes
            # try:
            #     for attrib in self.NETCDF_VAR_ATTRIBUTES[var]:
            #         ds[var].attrs[attrib] = self.NETCDF_VAR_ATTRIBUTES[var][attrib]
            #
            # except KeyError:
            #     pass
        return ds

    ###################################################################################

    def to_grid(
        self,
        data=None,
        vars=None,
        gridtype="1x1",
        engine="python",
        return_data_for_gridding=False,
        averaging_kernels=None,
    ):
        """to_grid method that takes a xarray.Dataset object as input"""

        import numpy as np
        import xarray as xr

        if isinstance(data, dict):
            _data = self.to_xarray(data_to_write=data)
        else:
            _data = self.to_xarray(data_to_write=data._data)

        if gridtype not in self.SUPPORTED_GRIDS:
            temp = f"Error: Unknown grid: {gridtype}"
            return

        if engine == "python":
            data_for_gridding, gridded_var_data = self._to_grid_grid_init(
                gridtype=gridtype, vars=vars, init_time=_data["time"].mean()
            )

            grid_lats = self.SUPPORTED_GRIDS[gridtype]["grid_lats"]
            grid_lons = self.SUPPORTED_GRIDS[gridtype]["grid_lons"]
            grid_dist_lat = self.SUPPORTED_GRIDS[gridtype]["grid_dist_lat"]
            grid_dist_lon = self.SUPPORTED_GRIDS[gridtype]["grid_dist_lon"]

            start_time = time.perf_counter()
            matching_points = 0
            # predefine the output data dict
            # data_for_gridding = {}

            # Loop through the output grid and collect data
            # store that in data_for_gridding[var]
            for lat_idx, grid_lat in enumerate(grid_lats):
                diff_lat = np.absolute(_data[self._LATITUDENAME].data - grid_lat)
                lat_match_indexes = np.squeeze(np.where(diff_lat <= (grid_dist_lat / 2.0)))
                print(f"lat: {grid_lat}, matched indexes: {lat_match_indexes.size}")
                if lat_match_indexes.size == 0:
                    continue

                for lon_idx, grid_lon in enumerate(grid_lons):
                    diff_lon = np.absolute(
                        _data[self._LONGITUDENAME].data[lat_match_indexes] - grid_lon
                    )
                    lon_match_indexes = np.squeeze(np.where(diff_lon <= (grid_dist_lon / 2.0)))
                    if lon_match_indexes.size == 0:
                        continue

                    for var in vars:
                        if return_data_for_gridding:
                            data_for_gridding[var][grid_lat][grid_lon] = np.array(
                                _data[self._LONGITUDENAME].data[
                                    lat_match_indexes[lon_match_indexes]
                                ]
                            )
                            # np.array(data[lat_match_indexes[lon_match_indexes], self.INDEX_DICT[var]])

                        less_than_zero_indexes = np.where(
                            _data[var].data[lat_match_indexes[lon_match_indexes]] > 0.0
                        )

                        try:
                            gridded_var_data[var]["mean"][lat_idx, lon_idx] = np.nanmean(
                                _data[var].data[
                                    lat_match_indexes[lon_match_indexes[less_than_zero_indexes]]
                                ]
                            )
                            gridded_var_data[var]["stddev"][lat_idx, lon_idx] = np.nanstd(
                                _data[var].data[
                                    lat_match_indexes[lon_match_indexes[less_than_zero_indexes]]
                                ]
                            )
                            gridded_var_data[var]["numobs"][lat_idx, lon_idx] = (
                                _data[var].data[lat_match_indexes[lon_match_indexes]].size
                            )
                            matching_points = (
                                matching_points
                                + _data[var]
                                .data[lat_match_indexes[lon_match_indexes[less_than_zero_indexes]]]
                                .size
                            )
                        except IndexError:
                            continue

            end_time = time.perf_counter()
            elapsed_sec = end_time - start_time
            temp = f"time for global {gridtype} gridding with python data types [s]: {elapsed_sec:.3f}"
            self.logger.info(temp)
            temp = f"matched {matching_points} points out of {_data['time'].size} existing points to grid"
            self.logger.info(temp)

            if return_data_for_gridding:
                self.logger.info("returning also data_for_gridding...")
                return gridded_var_data, data_for_gridding
            else:
                return gridded_var_data

        else:
            # 1 by on degree grid on emep domain
            pass

        if isinstance(data, xr.Dataset):
            pass
        else:
            super().to_grid(
                data=None,
                vars=None,
                gridtype=gridtype,
                engine="python",
                return_data_for_gridding=False,
            )

    ###################################################################################

    #####################################################################################

    def select_bbox(self, data=None, vars=None, bbox=None):
        """override base class method to work on with the read dictionary

        works on L2 data only

        """
        if data is None:
            _data = self.data
        else:
            try:
                _data = data._data
            except AttributeError:
                _data = data

        if isinstance(_data, dict):
            # write out the read data using the dictionary directly
            pass

            import time

            start = time.perf_counter()

            # ret_data = np.empty([self._ROWNO, self._COLNO], dtype=np.float_)
            # index_counter = 0
            # cut_flag = True
            # data = _data._data

            if bbox is not None:
                self.logger.info(bbox)
                lat_min = bbox[0]
                lat_max = bbox[1]
                lon_min = bbox[2]
                lon_max = bbox[3]

                # np.where can unfortunately only work with a single criterion
                matching_indexes_lat_max = np.where(_data[self._LATITUDENAME] <= lat_max)

                lats_remaining = _data[self._LATITUDENAME][matching_indexes_lat_max[0]]
                matching_indexes_lat_min = np.where(
                    _data[self._LATITUDENAME][matching_indexes_lat_max[0]] >= lat_min
                )
                lats_remaining = _data[self._LATITUDENAME][
                    matching_indexes_lat_max[0][matching_indexes_lat_min[0]]
                ]

                matching_indexes = np.where(ret_data[:, self._LATINDEX] <= lat_max)
                ret_data = ret_data[matching_indexes[0], :]
                # self.logger.warning('len after lat_max: {}'.format(len(ret_data)))
                matching_indexes = np.where(ret_data[:, self._LATINDEX] >= lat_min)
                ret_data = ret_data[matching_indexes[0], :]
                # self.logger.warning('len after lat_min: {}'.format(len(ret_data)))
                matching_indexes = np.where(ret_data[:, self._LONINDEX] <= lon_max)
                ret_data = ret_data[matching_indexes[0], :]
                # self.logger.warning('len after lon_max: {}'.format(len(ret_data)))
                matching_indexes = np.where(ret_data[:, self._LONINDEX] >= lon_min)
                ret_data = ret_data[matching_indexes[0], :]
                # self.logger.warning('len after lon_min: {}'.format(len(ret_data)))
                # matching_length = len(matching_indexes[0])
                _data._data = ret_data
                return _data

        else:
            super().select_bbox(_data, bbox)
