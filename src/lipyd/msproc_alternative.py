#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#  This file is part of the `lipyd` python module
#
#  Copyright (c) 2015-2019 - EMBL
#
#  File author(s):
#  Dénes Türei (turei.denes@gmail.com)
#  Igor Bulanov
#
#  Distributed under the GNU GPLv3 License.
#  See accompanying file LICENSE.txt or copy at
#      http://www.gnu.org/licenses/gpl-3.0.html
#
#  Website: https://saezlab.github.io/lipyd
#

from future.utils import iteritems

import os
import imp
import re

import numpy as np
import pyopenms as oms

import lipyd.session as session
import lipyd.common as common
import lipyd.settings as settings


class MethodParamHandler(session.Logger):
    """
    Base class for setup and check parameters for all derived classes.
    
    Parameters
    ----------
    **kwargs
        Parameters for the OpenMS object as keyword arguments.

    Attributes
    ----------
    openms_method : class
        OpenMS class having ``setParameters`` method.
    openms_obj : object
        OpenMS object having ``setParameters`` method.
    """
    
    
    _module_param_keys = {
        oms.PeakPickerHiRes: 'peak_picking_param',
        oms.ElutionPeakDetection: (
            'feature_finding_common_param',
            'elution_peak_detection_param',
        ),
        oms.MassTraceDetection: (
            'feature_finding_common_param',
            'mass_trace_detection_param',
        ),
        oms.FeatureFindingMetabo: (
            'feature_finding_common_param',
            'feature_finding_metabo_param',
        ),
        oms.MapAlignmentAlgorithmPoseClustering: 'map_alignment_param',
    }
    
    
    def __init__(self, name = 'param_handler', **kwargs):
        
        # most of the times log initialized in the OpenmsMethodWrapper
        if not hasattr(self, '_log_name'):
            
            session.Logger.__init__(self, name = name)
        
        self.openms_method = openms_method
        self._kwargs_param = kwargs
    
    
    def main(self):
        
        self.setup()
    
    
    def setup(self):
        """
        Collects and updates parameters according to the OpenMS object type.
        """
        
        self.get_openms_object_name()
        self.collect_param()
        self.set_param()
    
    
    def get_openms_object_name(self):
        """
        Creates a string representation of the OpenMS object type.
        """
        
        self.openms_object_type = '%s.%s' % (
            self.openms_method.__module__,
            self.openms_method.__name__,
        )
    
    
    def collect_param(self):
        """
        Collects parameters from (1) keyword arguments for this class,
        (2) settings of the `lipyd` module and (3) OpenMS defaults in this
        order of priority.
        """
        
        self.get_openms_defaults()
        self.get_module_param()
        
        _kwargs_param = self.process_param_dict(self._kwargs_param)
        _module_param = self.process_param_dict(self._module_param)
        self.param = {}
        
        self.param.update(self._openms_defaults)
        self.param.update(_module_param)
        self.param.update(_kwarg_param)
    
    
    def set_param(self):
        """
        Sets the parameters of the OpenMS object according to the current
        `param` dictionary.
        """
        
        self.openms_param = self.openms_obj.getDefaults()
        
        for key, value in iteritems(self.param):
            
            self.openms_param.setValue(key, value)
            
            self._log(
                'Parameter `{}` of `{}` set to `{}`.'.format(
                    common.ensure_unicode(name),
                    self.openms_obj_name,
                    common.ensure_unicode(value),
                ),
                1,
            )
        
        self.openms_obj.setParameters(self.openms_param)
    
    
    @staticmethod
    def bytes_or_numeric(value, float_ok = True):
        """
        Returns the `value` in a bytes string or a numeric representation.
        """
        
        if isinstance(value, bool):
            
            return value.__str__().lower().encode()
            
        elif isinstance(value, np.float64):
            
            return float(value)
            
        elif isinstance(value, (int, float)):
            
            return value
            
        elif (common.is_numeric(value) and float_ok) or common.is_int(value):
            
            return common.to_number(value)
            
        elif hasattr(value, 'encode'):
            
            return value.encode()
            
        else:
            
            return value
    
    
    @staticmethod
    def process_param_dict(param):
        """
        Makes sure all keys and values in the dict are byte strings or
        numeric.
        """
        
        return dict(
            (
                self.bytes_or_numeric(k, float_ok = False),
                self.bytes_or_numeric(v)
            )
            for k, v in iteritems(param)
        )
    
    
    def get_openms_defaults(self):
        """
        Queries the default parameter values from the OpenMS object and
        converts them to a `dict`.
        """
        
        # get the defaults from openms
        self._openms_defaults = dict(self.openms_obj.getDefaults())
    
    
    def get_module_param(self):
        """
        Queries the current module level settings of `lipyd` for the
        particular OpenMS class.
        """
        
        self._module_param = {}
        
        if self.openms_method in self._module_param_keys:
            
            self._log(
                'Could not find settings key for OpenMS '
                'object type `%s`.' % self.openms_obj_name
            )
            
        else:
            
            for key in self._module_param_keys[self.openms_method]:
                
                self._module_param.update(settings.get(key))


class MethodPathHandler(session.Logger):
    """
    Parameters
    ----------
    input_path : str
        The path of the input file must be provided, otherwise this class
        will do nothing. In case of multiple input files you can provide
        a list of paths or the directory containing the files.
    method_key : str,class
        Either an OpenMS class or a string label. Used to identify the
        method and look up the corresponding settings.
    sample_id_method : callable
        A method which generates sample identifier(s) from the input path(s).
        If not provided, the file name without the extension will be used.
    input_ext : str
        In case of multiple input files only the files with this extension
        (type) will be used.
    input_filter : callable,str
        A method which decides if an input file should be used. Should return
        ``True`` if the file is to be used. Alternatively a regex as a string
        which matches the desired input files.
    
    Attributes
    ----------
    multi_file_input : bool
        Tells if the object has single or multiple input paths.
    """
    
    _method_keys = {
        oms.PeakPickerHiRes: 'centroided',
        oms.FeatureFindingMetabo: 'feature',
        oms.MapAlignmentAlgorithmPoseClustering: 'aligned',
    }
    _outexts = {
        'centroided': 'mzML',
        'feature': 'featureXML',
        'aligned': 'featureXML',
        'msproc': 'featureXML',
    }
    
    
    def __init__(
            self,
            input_path = None,
            input_obj = None,
            method_key = None,
            output_path = None,
            sample_id = None,
            sample_id_method = None,
            input_ext = None,
            input_filter = None,
            name = 'path_handler',
        ):
        
        # most of the times log initialized in the OpenmsMethodWrapper
        if not hasattr(self, '_log_name'):
            
            session.Logger.__init__(self, name = name)
        
        self._input_path = input_path
        self.input_obj = input_obj
        self._input_ext = input_ext
        self._input_filter = input_filter
        self.output_path = output_path
        self.method_key = method_key
        self._sample_id_method = _sample_id_method
        self.sample_id = sample_id
    
    
    def main(self):
        
        self.set_paths()
    
    
    def set_paths(self):
        
        if self._input_path:
            
            self._set_input_path()
            self._set_sample_id()
            
            if not self.output_path:
                
                self._set_method_key()
                self._set_output_dir()
                self._set_output_path()
            
            self._create_output_dir()
            self._tell_paths()
            self._check_paths()
    
    
    def _set_input_path(self):
        
        if isinstance(self._input_path, common.basestring):
            
            # check if this is a directory
            if os.path.isdir(self._input_path):
                
                # look up all files in the directory
                self._input_path = [
                    os.path.join(self._input_path, fname)
                    for fname in os.listdir(self._input_path)
                ]
        
        # if we have something else than a single existing file path
        self.multi_file_input = not (
            isinstance(self._input_path, common.basestring) and
            os.path.exists(self._input_path)
        )
        
        if self.multi_file_input:
            
            self._filter_input_paths()
            # the `input_path` will be just the first file
            # just to make it easier for the downstream methods
            self.input_path = self._input_path[0]
            
        else:
            
            # the simple case when we have only one file
            self.input_path = self._input_path
    
    
    def _filter_input_paths(self):
        
        if isinstance(self._input_filter, common.basestring):
            
            refname = re.compile(self._input_filter)
            
            def _input_filter(path):
                
                return bool(refname.fullmatch(path))
            
            self._input_filter = _input_filter
        
        self._input_path = [
            path
            for path in self._input_path
            if (
                self._input_ext is None or
                os.path.splitext()[1] == self._input_ext
            ) and (
                self._input_filter is None or
                # this method recieves only the file name
                self._input_filter(os.path.basename(path))
            )
        ]
    
    
    def _set_output_dir(self):
        
        output_root = (
            # 1: output path explicitely set
            settings.get('output_path_root') or (
                # 2: it's set to be in the input dir
                os.path.dirname(self.input_path)
                    if settings.get('output_to_input_dir') else
                # 3: by default in current wd
                os.getcwd('output_to_input_dir')
            )
        )
        
        lipyd_wd = settings.get('lipyd_wd') or ''
        
        method_wd = settings.get('%s_dir' % self.method_key) or ''
        
        self.output_dir = os.path.join(
            output_root,
            lipyd_wd,
            method_wd,
        )
    
    
    def _create_output_dir(self):
        
        os.makedirs(self.output_dir, exist_ok = True)
    
    
    def _set_output_path(self):
        
        suffix = settings.get('%s_suffix' % self.method_key) or ''
        
        if isinstance(self.input_path, common.basestring):
            
            self._input_basename, ext = (
                os.path.splitext(os.path.basename(self.input_path))
            )
            
        else:
            
            self._input_basename = self.sample_id
        
        outext = (
            self._outexts[self.method_key]
                if self.method_key in self._outexts else
            'mzML'
        )
        self.outfile = '%s%s.%s' % (self._input_basename, suffix, outext)
        
        self.output_path = os.path.join(self.output_dir, self.outfile)
    
    
    def _set_method_key(self):
        
        if not self.method_key and self.openms_method in self._method_keys:
            
            self.method_key = self._method_keys[self.openms_method]
    
    
    def _tell_paths(self):
        """
        Writes the paths to the log.
        """
        
        self._log('Reading input from `%s`.' % self.input_path)
        self._log('Writing output to `%s`.' % self.output_path)
    
    
    def _check_paths(self):
        """
        Raising exception if input and output paths are identical.
        """
        
        if self.input_path == self.output_path:
            
            self._log(
                'The input and output files are identical: `%s`. '
                'You can set different output path either directly '
                'providing the `output_path` argument or changing '
                'parameters by the `lipyd.settings` module.' % (
                    self.output_path
                )
            )
            
            raise RuntimeError('Identical in/out path, please check the log.')
    
    
    def _set_sample_id(self):
        
        if not self.sample_id:
            
            if self.multi_file_input:
                
                self.sample_id = [
                    self._get_sample_id(path)
                    for path in self.input_path
                ]
                
            else:
                
                self.sample_id = self._get_sample_id(self.input_path)
    
    
    def _get_sample_id(self, path):
        
        if path:
            
            name = os.path.splitext(os.path.basename(path))[0]
        
        if self._sample_id_method is None:
            
            sample_id = name
            
        elif callable(self._sample_id_method):
            
            sample_id = self._sample_id_method(name)
            
        else:
            
            sample_id = self._sample_id_method
        
        return sample_id


class OpenmsMethodWrapper(MethodParamHandler, MethodPathHandler):
    """
    Generic base class for OpenMS method wrappers.
    
    Parameters
    ----------
    method : class
        The OpenMS class.
    infile : str
        The input file must be provided, otherwise no input and output
        assumed and only the parameters will be set.
    name : str
        A name for this method, will appear in the log.
    outfile : str
        Output path provided directly. Otherwise will be set according to
        the current settings.
    method_key : str
        
    """
    
    def __init__(
            self,
            method,
            input_path = None,
            input_obj = None,
            name = None,
            output_path = None,
            method_key = None,
            sample_id = None,
            sample_id_method = None,
            **kwargs
        ):
        
        session.Logger.__init__(self, name = name or 'openms_wrapper')
        
        self.openms_method = method
        
        MethodParamHandler.__init__(**kwargs)
        
        MethodPathHandler.__init__(
            input_path = input_path,
            input_obj = input_obj,
            method = method_key,
            output_path = output_path,
            sample_id = sample_id,
            sample_id_method = sample_id_method,
        )
    
    
    def main(self):
        
        self.openms_wrapper_setup()
        self.run()
    
    
    def openms_wrapper_setup(self):
        
        self.create_instance()
        self.setup()
        self.set_paths()
    
    
    def create_instance(self):
        
        self.openms_obj = self.openms_method()
        self._log(
            '`%s.%s` instance created.' % (
                self.openms_method.__module__,
                self.openms_method.__name__,
            )
        )
    
    
    def run(self):
        
        pass


class PeakPickerHiRes(OpenmsMethodWrapper):
    """
    Wrapper around ``pyopenms.PeakPickerHiRes``.
    
    This class implements a fast peak-picking algorithm best suited for high
    resolution MS data (FT-ICR-MS, Orbitrap). In high resolution data, the
    signals of ions with similar mass-to-charge ratios (m/z) exhibit little
    or no overlapping and therefore allow for a clear separation. Furthermore,
    ion signals tend to show well-defined peak shapes with narrow peak width.

    This peak-picking algorithm detects ion signals in profile data and
    reconstructs the corresponding peak shape by cubic spline interpolation.
    Signal detection depends on the signal-to-noise ratio which is adjustable
    by the user (see parameter signal_to_noise). A picked peak's m/z and
    intensity value is given by the maximum of the underlying peak spline.

    So far, this peak picker was mainly tested on high resolution data. With
    appropriate preprocessing steps (e.g. noise reduction and baseline
    subtraction), it might be also applied to low resolution data.

    Parameters
    ----------
    infile : str
        Input file mzML with profile data.
    outfile : str
        The output file can be set directly this way. Alternatively see
        the built in path handling parameters in `settings`.
    **kwargs
        Settings passed directly to ``pyopenms.PeakPickerHiRes``.
    """
    
    
    def __init__(
            self,
            input_path = None,
            input_obj = None,
            output_path = None,
            sample_id = None,
            sample_id_method = None,
            **kwargs,
        ):
        
        OpenmsMethodWrapper.__init__(
            self,
            method = oms.PeakPickerHiRes,
            input_path = input_path,
            input_obj = input_obj,
            output_path = output_path,
            name = 'peak_picker',
            sample_id = sample_id,
            sample_id_method = sample_id_method,
            **kwargs
        )
    
    
    def run(self):
        
        self.read()
        self.pick()
        self.write()
    
    
    def read(self):
        
        if isinstance(self.input_obj, oms.MSExperiment):
            
            self.input_map = self.input_obj
            self._log('Input map provided as `pyopenms.MSExperiment` object.')
            
        else:
            
            self.input_map = oms.MSExperiment()
            oms.MzMLFile().load(self.input_path, self.input_map)
            self._log('Input map created from `%s`.' % self.input_path)
    
    
    def pick(self):
        
        self._log('Starting peak picking.')
        self.output_map = oms.MSExperiment()
        self.openms_obj.pickExperiment(self.input_map, self.output_map)
        self._log('Peak picking ready.')
    
    
    def write(self):
        
        self.output_map.updateRanges()
        oms.MzMLFile().store(self.output_path, self.output_map)
        self._log(
            'Centroided data has been written to `%s`.' % self.output_path
        )


class MassTraceDetection(OpenmsMethodWrapper):
    """
    Wrapper around ``pyopenms.MassTraceDetection``.
    """
    
    
    def __init__(self, **kwargs):
        
        OpenmsMethodWrapper.__init__(
            self,
            method = oms.MassTraceDetection,
            name = 'mass_trace_detection',
        )


class ElutionPeakDetection(OpenmsMethodWrapper):
    """
    Wrapper around ``pyopenms.ElutionPeakDetection``.
    """
    
    
    def __init__(self, **kwargs):
        
        OpenmsMethodWrapper.__init__(
            self,
            method = oms.ElutionPeakDetection,
            name = 'elution_peak_detection',
        )


class FeatureFindingMetabo(OpenmsMethodWrapper):
    """
    Wrapper around ``pyopenms.FeatureFindingMetabo()``.
    Assembles mass traces showing similar isotope- and elution patterns.
    
    Parameters
    ----------
    input_file : str
        Path to an mzML file with centroided data.
    input_map : pyopenms.PeakMap
        A``pyopenms.PeakMap`` object. If provided, the data will be used
        from this instead of reading from ``input_file``. In this case
        ``input_file`` can be even ``None`` if ``output_file`` provided.
        Otherwise ``input_file`` will be used to create the ``output_file``
        path and name.
    output_file : str
        The output file where the features will be saved in ``featureXML``
        format. If not provided it will be set according to the current
        settings.
    mass_trace_detection_param : dict
        Parameters directly for the ``pyopenms.MassTraceDetection`` class.
    elution_peak_detection_param : dict
        Parameters directly for the ``pyopenms.ElutionPeakDetection`` class.
    feature_finding_metabo_param : dict
        Parameters directly for the ``pyopenms.FeatureFindingMetabo`` class.
    **kwargs
        Common parameters will be passed to all of the OpenMS methods above.
    """
    
    
    def __init__(
        self,
        input_file = None,
        input_map = None,
        output_file = None,
        sample_id = None,
        sample_id_method = None,
        mass_trace_detection_param = None,
        elution_peak_detection_param = None,
        feature_finding_metabo_param = None,
        **kwargs
    ):
        
        self.mass_trace_detection_param = (
            self._combine_param(kwargs, mass_trace_detection_param)
        )
        self.elution_peak_detection_param = (
            self._combine_param(kwargs, elution_peak_detection_param)
        )
        self.feature_finding_metabo_param = (
            self._combine_param(kwargs, feature_finding_metabo_param)
        )
        
        if isinstance(input_map, oms.PeakMap):
            
            self.input_map = input_map
            self._log(
                'Centroided data provided as `pyopenms.PeakMap` object.'
            )
        
        OpenmsMethodWrapper.__init__(
            self,
            method = oms.FeatureFindingMetabo,
            infile = input_file,
            outfile = output_file,
            name = 'feature_finding_metabo',
            sample_id = sample_id,
            sample_id_method = sample_id_method,
            **self.feature_finding_metabo_param,
        )
    
    
    def run(self):
        
        self.read()
        self.find_features()
        self.write()
    
    
    def read(self):
        """
        Reads the centroided data.
        """
        
        if not hasattr(self, 'input_map'):
            
            self.input_map = oms.PeakMap()
            oms.MzMLFile().load(self.input_path, self.input_map)
            self._log('Reading centroided data from `%s`.' % self.input_path)
    
    
    def find_features(self):
        
        self.do_mass_trace_detection()
        self.do_elution_peak_detection()
        self.do_feature_finding()
        self._log('Feature finding ready.')
    
    
    def do_mass_trace_detection(self):
        
        self._log('Performing mass trace detection.')
        self.mass_traces = []
        self.mass_trace_detection = MassTraceDetection(
            **self.mass_trace_detection_param
        )
        self.mass_trace_detection.run(self.input_map, self.mass_traces)
    
    
    def do_elution_peak_detection(self):
        
        self._log('Performing elution peak detection.')
        self.mass_traces_split = []
        self.elution_peak_detection = ElutionPeakDetection(
            **self.elution_peak_detection_param
        )
        self.elution_peak_detection.detectPeaks(
            self.mass_traces,
            self.mass_traces_split,
        )
    
    
    def do_feature_finding(self):
        
        self._log('Creating features by `FeatureFinderMetabo`.')
        self.feature_map = oms.FeatureMap()
        self.mass_traces_filtered = []
        self.feature_finder_metabo = self.openms_obj
        self.feature_finder_metabo.run(
            self.mass_traces_split,
            self.feature_map,
            self.mass_traces_filtered,
        )
    
    
    def write(self):
        """
        Writes the feature map into a ``featureXML`` file.
        """
        
        oms.FeatureXMLFile().store(self.output_path, self.feature_map)
        self._log('Features have been written to `%s`.' % self.output_path)
    
    
    @staticmethod
    def _combine_param(common_param, param):
        
        combined_param = copy.deepcopy(kwargs) or {}
        combined_param.update(param or {})
        
        return combined_param


class MapAlignmentAlgorithmPoseClustering(OpenmsMethodWrapper):
    """
    Applies a transformation on a feature map along its RT and m/z dimensions
    in order to remove noise and align traces from identical metabolites.
    
    Wrapper around ``pyopenms.MapAlignmentAlgorithmPoseClustering``.
    
    A map alignment algorithm based on pose clustering.

    Pose clustering analyzes pair distances to find the most probable
    transformation of retention times.
    The algorithm chooses the x most intensive peaks/features per map.
    This is modeled via the parameter ``max_num_peaks_considered``,
    which in turn influences the runtime and stability of the results.
    Bigger values prolong computation, smaller values might lead to no or
    unstable trafos. Set to -1 to use all features (might take very long for
    large maps).
    
    Parameters
    ----------
    input_file : str
        Path to a featureXML file.
    input_map : pyopenms.FeatureMap
        A``pyopenms.FeatureMap`` object. If provided, the data will be used
        from this instead of reading from ``input_file``. In this case
        ``input_file`` can be even ``None`` if ``output_file`` provided.
        Otherwise ``input_file`` will be used to create the ``output_file``
        path and name.
    output_file : str
        The output featureCML file where the aligned features will be saved
        If not provided it will be set according to the current settings.
    reference_file : str
        Path to the reference featureXML. The features will be aligned to
        this map.
    reference_map : pyopenms.FeatureMap
        A ``FeatureMap`` object instead of the file above. This way the
        reference features do not need to be read again.
    **kwargs
        Passed directly to ``pyopenms.MapAlignmentAlgorithmPoseClustering``.
    """
    
    
    def __init__(
            self,
            input_file = None,
            input_map = None,
            output_file = None,
            reference_file = None,
            reference_map = None,
            sample_id = None,
            sample_id_method = None,
            **kwargs
        ):
        
        OpenmsMethodWrapper.__init__(
            self,
            input_file = input_file,
            output_file = output_file,
            sample_id = sample_id,
            sample_id_method = sample_id_method,
            name = 'map_aligner',
            **kwargs,
        )
        
        self.input_map = input_map
        self.reference_map = reference_map
    
    
    def run(self):
        
        self.read_input()
        self.read_reference()
        self.align()
        self.write()
    
    
    def read_input(self):
        
        self._log('Obtaining input feature map.')
        
        self.input_map = self.read(
            path = self.input_path,
            mapobject = self.input_map,
        )
    
    
    def read_reference(self):
        
        self._log('Obtaining reference feature map.')
        
        self.reference_map = self.read(
            path = self.reference_path,
            mapobject = self.reference_map,
        )
    
    
    def read(self, path, mapobject):
        
        if not isinstance(mapobject, oms.FeatureMap):
            
            mapobject = oms.FeatureMap()
            oms.FeatureXMLFile().load(path, mapobject)
            self._log('Feature map has been read from `%s`.' % path)
            
        else:
            
            self._log('Using the provided `pyopenms.FeatureMap` object.')
        
        return mapobject
    
    
    def align(self):
        
        self._log('Aligning the input map to the reference map.')
        # set reference_map file
        self.openms_obj.setReference(self.reference_map)
        # create object for the computed transformation
        self.transformation = oms.TransformationDescription()
        # do the alignment
        self.openms_obj.align(self.input_map, self.transformation)
    
    
    def write(self):
        
        oms.FeatureXMLFile().store(self.output_path, self.output_map)
        self._log(
            'Aligned features have been written to `%s`.' % self.output_path
        )


class MgfExport(MethodPathHandler):
    """
    Exports the MS2 spectra in mascot generic format (MGF).
    
    Parameters
    ----------
    input_file : str
        Path to the mz
    """
    
    def __init__(
        self,
        input_file = None,
        input_data = None,
        output_file = None,
        sample_id = None,
        sample_id_method = None,
    ):
        
        MethodPathHandler.__init__(
            input_file = input_file,
            output_file = output_file,
            name = 'mgf_export',
            method_key = 'mgf_export',
            sample_id = sample_id,
            sample_id_method = sample_id_method,
        )
        
        self.data = input_data
    
    
    def main(self):
        
        self.set_paths()
        self.read()
        self.write()
    
    
    def read(self):
        
        if not isinstance(self.data, oms.MSExperiment):
            
            mzml_file = oms.MzMLFile()
            self.data = oms.MSExperiment()
            mzml_file.load(self.input_path, self.data)
            self._log('Reading MS2 spectra from `%s`.' % self.input_path)
            
        else:
            
            self._log(
                'Using MS2 spectra from `pyopenms.MSExperiment` object.'
            )
    
    
    def write(self):
        
        with open(self.output_path, 'w') as fp:
            
            self._log('Exporting MS2 spectra to `%s`.' % self.output_path)
            # I commented this out at the moment,
            # I am not sure we need it:
            # Create header
            #outfile.write("COM=Testfile\n")
            #outfile.write("ITOL=1\n")
            #outfile.write("ITOLU=Da\n")
            #outfile.write("CLE=Trypsin\n")
            #outfile.write("CHARGE=1,2,3\n")
            
            # Iterate through all spectra,
            # skip all MS1 spectra and then write mgf format
            nr_ms2_spectra = 0
            
            for spectrum in self.data:
                
                if spectrum.getMSLevel() == 1:
                    continue
                
                nr_ms2_spectra += 1
                _ = fp.write("BEGIN IONS\n")
                _ = fp.write("TITLE=%s\n" % spectrum.getNativeID())
                _ = fp.write("RTINSECONDS=%.09f\n" % spectrum.getRT())
                
                try:
                    _ = fp.write(
                        "PEPMASS=%.018f %.09f\n" % (
                            spectrum.getPrecursors()[0].getMZ(),
                            spectrum.getPrecursors()[0].getIntensity(),
                        )
                    )
                    ch = spectrum.getPrecursors()[0].getCharge()
                    
                    if ch > 0:
                        _ = fp.write("CHARGE=%u%s\n" % (
                                abs(ch),
                                '-' if ch < 0 else ''
                            )
                        )
                    
                except IndexError:
                    _ = fp.write("PEPMASS=unknown\n")
                
                for peak in spectrum:
                    _ = fp.write(
                        "%s %s\n" % (peak.getMZ(), peak.getIntensity())
                    )
                
                _ = fp.write("END IONS\n")
            
            if nr_ms2_spectra == 0:
                
                self._log(
                    'Could not find any MS2 spectra in the input, '
                    'the output MGF file is empty!',
                    -1,
                )
                
            else:
                
                self._log(
                    '%u spectra have been written to `%s`.' % self.output_path
                )


class MSPreprocess(MethodPathHandler):
    """
    
    Workflow covering all MS preprocessing steps: peak picking, feature
    construction, map alignment and feature grouping. Also exports MS2
    spectra in MGF format.
    
    Parameters
    ----------
    force : set
        A set of steps which must be done no matter if the output of a later
        stage is available. E.g. ``{'peak_picking'}``.
    stop : str
        A step where the workflow has to stop. E.g. if it's
        ``feature_finding``, the last step executed will be
        ``feature_finding``.
    """
    
    _steps = (
        ('profile', 'centroided', 'peak_picking'),
        ('centroided', 'features', 'feature_finding'),
        ('features', 'features_aligned', 'map_alignment'),
        ('features_aligned', 'features_grouped', 'feature_grouping'),
    )
    
    
    def __init__(
        self,
        # stages
        profile = None,
        centroided = None,
        features = None,
        features_aligned = None,
        features_grouped = None,
        # further parameters for input/output
        output_path = None,
        sample_id_method = None,
        sample_ids = None,
        input_ext = None,
        input_filter = None,
        # parameters for each step
        peak_picking_param = None,
        mass_trace_detection_param = None,
        elution_peak_detection_param = None,
        feature_finding_metabo_param = None,
        feature_finding_common_param = None,
        map_alignment_param = None,
        feature_grouping_param = None,
        # workflow parameters
        force = None,
        stop = None,
        # nothing
        **kwargs
    ):
        
        session.Logger.__init__(self, name = 'msproc')
        
        self.peak_picking_param = peak_picking_param or {}
        self.mass_trace_detection_param = mass_trace_detection_param or {}
        self.elution_peak_detection_param = elution_peak_detection_param or {}
        self.feature_finding_metabo_param = feature_finding_metabo_param or {}
        self.feature_finding_common_param = feature_finding_common_param or {}
        self.feature_finding_
        self.map_alignment_param = map_alignment_param or {}
        self.feature_grouping_param = feature_grouping_param or {}
        
        self.sample_ids = sample_ids
        self.force = force or set()
        self.profile = profile
        self.centroided = centroided
        self.features = features
        self.features_aligned = features_aligned
        self.features_grouped = features_grouped
        
        self.MethodPathHandler.__init__(
            self,
            input_path = input_path,
            input_obj = input_obj,
            output_path = output_path,
            sample_id_method = sample_id_method,
            input_ext = input_ext,
            input_filter = input_filter,
        )
        
        self._input = (
            self.input_obj if self.input_obj is not None else self.input_path
        )
        self._input = (
            self._input
                if isinstance(self._input, (tuple, list, np.ndarray)) else
            (self._input,)
        )
        self._input_arg = (
            'input_obj' if self.input_obj is not None else 'input_path'
        )
    
    
    def main(self):
        
        self.workflow()
    
    
    def workflow(self):
        
        for source, result, method in self._steps:
            
            if not getattr(self, result) or method in self.force:
                
                self._log('Next step in workflow: `%s`.' % method)
                getattr(self, method)()
            
            if method == self.stop:
                
                break
    
    
    def peak_picking(self):
        
        self.centroided = []
        
        for resource in self.profile:
            
            self.peak_picking_param[self._input_arg] = resource
            
            peak_picker = PeakPickerHiRes(**self.peak_picking_param)
            peak_picker.main()
            self.centroided.append(peak_picker.output_map)
            del self.peak_picking_param[self._input_arg]
    
    
    def feature_finding(self):
        
        self.features = []
        
        for resource in self.


class MSPreprocess(session.Logger):
    """
    
    Workflow covering all MS preprocessing steps: peak picking, feature
    construction, map alignment and feature grouping. Also exports MS2
    spectra in MGF format.
    
    Usage:
    
    Firstly, you need to define variable as preproc = Preprocessing()
    Secondly, you have to specify desirable parameters according to pyopenms
    library. You can see all parameters at
    https://abibuilder.informatik.uni-tuebingen.de/
    /archive/openms/Documentation/release/2.4.0/html/index.html or in the
    TOPP application in vocabulary view, e.g ``param_pp = {"signal_to_noise": 1.0}``.
    Note: Boolean values should be strings, e.g.
    ``param_epd = {"enabled": "true"}``.
    
    param_pp - variable for Peak Picking parameters
    param_ff_com - variable for common Feature Finding Metabo parameters
    param_mtd - variable for Mass Trace Detection (1st step of FFM) parameters
    param_epd - variable for Elution Peak Detection (2nd step) parameters
    param_ffm - variable for Feature Finder (3rd step) parameters
    param_ma - variable for Map Alignment process
    Thirdly you have to call next methods consistently:
    preproc.peak_picking(src = "/your source directory/",
                          dst = "/destination directory",
                          suffix_dst_files = "",
                          ext_dst_files = "mzML" or "featureXML")
    prerpoc.feature_finding_metabo (the same arguments)
    preproc.map_alignment (the same srguments)
    preproc.run()
    
    Parameters
    ----------
    src : str
        Source directory consists source file(s)
    dst :  str, optional
        Destination directory
    suffix_dst_files : str, optional
        Additional part of result file name
    ext_dst_files: str, optional
        Extension of resulting files
    
    """

    def __init__(
            self,
            src = None,
            dst = None,
            mzs = None,
            intensities = None,
            rts = None
        ):

        session.Logger.__init__(self, name = 'Preprocessing')

        self.pp = None
        self.ff = None
        self.ma = None

        self.src = src
        self.dst = dst

        self.mzs = mzs
        self.intensities = intensities
        self.rts = rts
        
    def peak_picking(self,
                src = None,
                dst = None,
                suffix_dst_files = "_picked",
                ext_dst_files = "mzML",
                **param):
        
        self.pp = PeakPicking(
                src = src,
                dst = dst,
                suffix_dst_files = "_picked",          #for example : "_feature"
                ext_dst_files = "mzML",           #the string may begin with a dot
                **param)

    def feature_finding_metabo(self,
                src = None,
                dst = None,
                suffix_dst_files = "_feature",
                ext_dst_files = "featureXML",
                **param):
        
        self.ff = FeatureFindingMetabo(
                src = src,
                dst = dst,
                suffix_dst_files = suffix_dst_files, #for example : "_feature"
                ext_dst_files = ext_dst_files,       #the string may begin with a dot
                **param)

    def map_alignment(self,
                src = None,
                dst = None,
                suffix_dst_files = "",
                ext_dst_files = "featureXML",
                reference_file = None,
                **param):
        
        self.ma = MapAlignment(
                src = src,
                dst = dst,
                reference_file = reference_file,
                suffix_dst_files = suffix_dst_files, #for example : "_feature"
                ext_dst_files = ext_dst_files,       #the string may begin with a dot
                **param)


    def setup_pp_params(self, **param):
        self.pp.pp.set_parameters(**param)


    def setup_ff_mtd_params(self, **param):
        self.ff.set_param_mtd(**param)

    def setup_ff_epd_params(self, **param):
        self.ff.set_param_epd(**param)

    def setup_ff_ffm_params(self, **param):
        self.ff.set_param_ffm(**param)

    def setup_ma_params(self, **param ):
        self.ma.ma.set_parameters(**param)

    def run(self):
        
        self.pp.main()
        self.ff.main()
        self.ma.main()


    def get_sampleset(self, src):
        """
        Methods for extracting mzs, rts, intensities from all files
        as 2 dimensional arrays

        """

        if not(src or self.src):
            raise RuntimeError("you have to point src pattern.")
        
        src_pattern = src if src else self.src
        
        self.mzs = []
        self.intensities = []
        self.rts = []
        
        for f in get_list_full_names(src_pattern):
            
            xml_file = oms.FeatureXMLFile()
            fmap = oms.FeatureMap()
            xml_file.load(f, fmap)
            
            print("get_xml_data f=", f)
            
            rts_tmp = []
            mzs_tmp = []
            intensities_tmp = []
            
            for n in fmap:
                _rt = n.getRT()
                _mz = n.getMZ()
                _intensities = n.getIntensity()
                rts_tmp.append(_rt)
                mzs_tmp.append(_mz)
                intensities_tmp.append(_intensities)
            
            self.mzs.append(mzs_tmp)
            self.intensities.append(intensities_tmp)
            self.rts.append(rts_tmp)

        #print(rts. mzs. intensities)

        return {
            'mzs': self.mzs,
            'rts': self.rts,
            'intensities': self.intensities
        }  

    def get_sampleset_2(self, src):  
        """Another methods for extracting data"""  
        
        if not (src or self.src):
            raise RuntimeError("you have to point src pattern.")
        
        #override path pattern name to src;
        src_pattern = src if src else self.src

        self.mzs = []
        self.intensities = []
        self.rts = []
        
        for f in get_list_full_names(src_pattern):
            
            #print("get_data.f = ", f)
            mzml_file = oms.MzMLFile()
            exp = oms.MSExperiment()
            mzml_file.load(f, exp)  # f is current file name from list of names;
            
            rt_for_file = []        # rt list for this file;
            mzs_for_rt = []         # mz list of list for this rt;
            intensities_for_rt = []        # ints list of list for this rt;
            
            for spec in exp:        # spec is MSSpectrum type object;
                
                mzs_tmp = []
                intensities_tmp = []
                
                _rt = spec.getRT()
                rt_for_file.append(_rt)
                
                for p in spec:
                    _mz = p.getMZ()
                    _ints = p.getIntensity()
                    mzs_tmp.append(_mz)
                    intensities_tmp.append(_ints)
                    #print("get_data: _rt={}, _mz={}, _ints={} ".format(_rt, _mz, _ints) )

                mzs_for_rt.append(mzs_tmp)
                ints_for_rt.append(intensities_tmp)
            
            self.rts.append(rt_for_file) # add rt list for current file to global rt list;
            self.mzs.append(mzs_for_rt)  # same for mz;
            self.ints.append(ints_for_rt)# same for ints;
        
        return  {
            'mzs': self.mzs,
            'rt_means': self.rts,
            'intensities': self.intensities
        }
