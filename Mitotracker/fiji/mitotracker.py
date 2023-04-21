""" mitotracker.py: Trace mitochondria after live microscopy in time series."""


#@ File    (label = "Input directory", style = "directory") input_dir
#@ String    (label = "File type", value = ".czi") suffix


import os
import sys
import logging

import java.io.File as File

from ij import IJ, ImagePlus

from loci.plugins import BF
from emblcmci import BleachCorrection_MH

from fiji.plugin.trackmate import TrackMate, Model, Settings, Logger, SelectionModel

from fiji.plugin.trackmate.detection import DetectorKeys
from fiji.plugin.trackmate.stardist import StarDistDetectorFactory

from fiji.plugin.trackmate.providers import (
	DetectorProvider,
	TrackerProvider,
	SpotAnalyzerProvider,
	EdgeAnalyzerProvider,
	TrackAnalyzerProvider
)

from fiji.plugin.trackmate.tracking import LAPUtils
from fiji.plugin.trackmate.tracking.sparselap import SparseLAPTrackerFactory

from fiji.plugin.trackmate.features import (
	FeatureFilter,
	FeatureAnalyzer,
	ModelFeatureUpdater,
	SpotFeatureCalculator, 
	TrackFeatureCalculator
)
from fiji.plugin.trackmate.features.spot import (
	SpotAnalyzerFactory,
	SpotContrastAndSNRAnalyzerFactory,
	SpotContrastAndSNRAnalyzer, 
	SpotIntensityMultiCAnalyzerFactory
)

from fiji.plugin.trackmate.features.track import (
	TrackIndexAnalyzer,
	TrackDurationAnalyzer,
	TrackSpeedStatisticsAnalyzer
)

from fiji.plugin.trackmate.visualization import (
	TrackMateModelView,
	AbstractTrackMateModelView,
	PerTrackFeatureColorGenerator,
	PerEdgeFeatureColorGenerator,
	SpotColorGeneratorPerTrackFeature
)
from fiji.plugin.trackmate.visualization.hyperstack import HyperStackDisplayer
from fiji.plugin.trackmate.visualization.trackscheme import TrackScheme

from fiji.plugin.trackmate.action import (
	CaptureOverlayAction,
	ExportStatsTablesAction,
	ExportTracksToXML
)

from fiji.plugin.trackmate.io import TmXmlReader, TmXmlWriter

from fiji.plugin.trackmate.gui.displaysettings import DisplaySettingsIO
from fiji.plugin.trackmate.gui.displaysettings.DisplaySettings import (
	TrackMateObject,
	TrackDisplayMode
)


log = logging.basicConfig(filename = "Fiji_Py_Mitotracker_20220930.log", level=logging.NOTSET)


class imagefile:

	"""Image files for analysis in ImageJ and Fiji"""
	
	def __init__(self, path, filename):
		self.path = path
		self.filename = filename
		self.analysis_path = os.path.join(path, 'analysis')
		
	def open_imagefile(self):
		"""Open imagefile with BioFormats as ImagePlus."""
		print "    Open", self.filename
		imps = BF.openImagePlus(os.path.join(self.path, self.filename))
		for imp in imps:	
			self.imp = imp
	
	def calibrate(self):
		"""Get image calibration from imagefile (ImagePlus)."""
		print "    Calibrate", self.filename
		self.calibration = self.imp.getCalibration()
		self.nframes = self.imp.getNFrames()
		
	def adjust(self):
		"""Adjust contrast evenly for all frames in imagefile."""
		print "    Adjust", self.filename
		IJ.run(self.imp, "Enhance Contrast", "saturated=0.05")
		IJ.run(self.imp, "Apply LUT", "stack")
	
	def bleachcorrect(self):
		"""Correct bleaching across frames using histomgram matching (slow)."""
		print "    Correct bleaching in", self.filename
		bc = BleachCorrection_MH(self.imp)
		bc.doCorrection()
	
	def mkdir_analysis(self):
		if not os.path.exists(self.analysis_path):
			os.makedirs(self.analysis_path)
	
	def export_tiff(self):
		IJ.saveAs(
			self.imp,
			"Tiff",
			os.path.join(
				self.analysis_path,
				self.filename.replace(".czi", ".tif")
			)
		)
	
	def run_trackmate_mito(self):
		
		"""Run TrackMate 7 on imagefile to trace mitochondria."""
		
		print "    Trace mitochondria with TrackMate 7 in", self.filename
	
		# System Reload ----------------------------------------------------------------
		## Avoid errors with utf-8 encoding in Fiji and TrackMate
		reload(sys)
		sys.setdefaultencoding('utf-8')
		
		# Create Model -----------------------------------------------------------------
		self.model = Model()
		self.model.setLogger(Logger.IJ_LOGGER)
		self.model.setPhysicalUnits(self.calibration.getUnit(), self.calibration.getTimeUnit())
		
		# Prepare Settings -------------------------------------------------------------
		self.settings = Settings(self.imp)
		
		# Detector ---------------------------------------------------------------------
		self.settings.detectorFactory = StarDistDetectorFactory()
		self.settings.detectorSettings = {
			'TARGET_CHANNEL' : 1,
		}
		
		# Filter Spots -----------------------------------------------------------------
		filter1 = FeatureFilter('QUALITY', 0.0, True)
		self.settings.addSpotFilter(filter1)
		
		# Tracker
		self.settings.trackerFactory = SparseLAPTrackerFactory()
		self.settings.trackerSettings = LAPUtils.getDefaultLAPSettingsMap()
		
		## Linking
		self.settings.trackerSettings['LINKING_MAX_DISTANCE'] = 5.0 # double
		
		## Gap Closing
		self.settings.trackerSettings['ALLOW_GAP_CLOSING'] = True # boolean
		self.settings.trackerSettings['GAP_CLOSING_MAX_DISTANCE'] = 6.0 # double
		self.settings.trackerSettings['MAX_FRAME_GAP'] = 3 # integer
		
		## Track Merging
		self.settings.trackerSettings['ALLOW_TRACK_MERGING'] = True # boolean
		self.settings.trackerSettings['MERGING_MAX_DISTANCE'] = 5.0 # double
		
		## Track Splitting
		self.settings.trackerSettings['ALLOW_TRACK_SPLITTING'] = True # boolean
		self.settings.trackerSettings['SPLITTING_MAX_DISTANCE'] = 5.0 # double
		
		## Advanced settings
		self.settings.trackerSettings['ALTERNATIVE_LINKING_COST_FACTOR'] = 1.05 # double
		self.settings.trackerSettings['CUTOFF_PERCENTILE'] = 0.9 # double
		
		# Analyze Tracks ---------------------------------------------------------------
		self.settings.clearSpotAnalyzerFactories()
		self.settings.clearEdgeAnalyzers()
		self.settings.clearTrackAnalyzers()
		
		detectorProvider        = DetectorProvider()
		trackerProvider         = TrackerProvider()
		spotAnalyzerProvider    = SpotAnalyzerProvider(self.imp.getNChannels())
		edgeAnalyzerProvider    = EdgeAnalyzerProvider()
		trackAnalyzerProvider   = TrackAnalyzerProvider()
		
		for key in spotAnalyzerProvider.getKeys():
			self.settings.addSpotAnalyzerFactory(spotAnalyzerProvider.getFactory(key))
		for key in edgeAnalyzerProvider.getKeys():
			self.settings.addEdgeAnalyzer(edgeAnalyzerProvider.getFactory(key))
		for key in trackAnalyzerProvider.getKeys():
			self.settings.addTrackAnalyzer(trackAnalyzerProvider.getFactory(key))
		
		# Filter Tracks ----------------------------------------------------------------
		## filter2 = FeatureFilter('TRACK_DISPLACEMENT', 10, True)
		## self.settings.addTrackFilter(filter2)
		
		# Initiate TrackMate -----------------------------------------------------------
		self.trackmate = TrackMate(self.model, self.settings)
		self.trackmate.getModel().getLogger().log(self.settings.toStringFeatureAnalyzersInfo())
		self.trackmate.computeSpotFeatures(True)
		self.trackmate.computeEdgeFeatures(True)
		self.trackmate.computeTrackFeatures(True)
		
		# Process TrackMate-------------------------------------------------------------
		ok = self.trackmate.checkInput()
		if not ok:
			sys.exit(str(self.trackmate.getErrorMessage()))
		ok = self.trackmate.process()
		if not ok:
			sys.exit(str(self.trackmate.getErrorMessage()))
		
		# Selection Model --------------------------------------------------------------
		self.sm = SelectionModel(self.model)
		
		# Configure Display ------------------------------------------------------------
		self.ds = DisplaySettingsIO.readUserDefault()
		
		# Display Results --------------------------------------------------------------
		self.displayer = HyperStackDisplayer(self.model, self.sm, self.imp, self.ds)
		self.displayer.render()
		self.displayer.refresh()
		
		# Feature Model ----------------------------------------------------------------
		## The feature model contains tracks and edges (spots)
		self.fm = self.model.getFeatureModel()
	
	def capture_tm_overlay(self):
		capture = CaptureOverlayAction.capture(self.trackmate, -1, self.nframes, Logger.IJ_LOGGER)
		IJ.saveAs(
			capture,
			"Tiff",
			os.path.join(
				self.analysis_path,
				self.filename.replace(".czi", "_overlay.tif")
			)
		)

	def export_tm_xml(self):
		outXML = File(
			self.analysis_path,
			self.filename.replace(".czi", "_tm_model.xml")
		)
		writer = TmXmlWriter(outXML)
		writer.appendModel(self.model)
		writer.appendSettings(self.settings)
		writer.writeToFile()
			
	def close_imagefile(self):
		self.imp.changes = False
		self.imp.close()

def main(input_dir, suffix):
	
	## Correct inputs if necessary
	input_dir = str(input_dir)
	if not str(suffix):
		suffixes = ['.czi', '.tif', '.png', '.jpeg', '.jpg']
	else:
		suffixes = [str(suffix)]
	
	## Loop over directories and files
	for root, dirs, files in os.walk(input_dir):
	
		for dir in list(dirs):
			if dir.startswith('.') or dir in ["analysis", "results"]:
				dirs.remove(dir)
	
			print "Looking into ", str(root)
			for file in list(files):
				for suffix in suffixes:
					if suffix in file:
						
						print "  Found", str(file)
						
						## Create calibrated imagefile from file
						imf = imagefile(str(root), str(file))	
						imf.open_imagefile()
						imf.calibrate()
						
						## Pre-processing of time series and save as tiff
						imf.adjust()
						imf.bleachcorrect()
						imf.mkdir_analysis()
						
						## Track mitochondria
						imf.run_trackmate_mito()
						
						## Export mitochondrial traces (can be opened later again)
						imf.export_tm_xml()
						imf.capture_tm_overlay()

						## Close imagefile
						imf.close_imagefile()
	
	print "The End"
	#print "The value of __name__ is:", repr(__name__)


if __name__ == "__main__":
    main(input_dir, suffix)